from datetime import datetime
from flask import Flask, render_template, flash, request, redirect, url_for, jsonify
from flaskext.mysql import MySQL
from preston_new import Preston

import time
import yaml

application = Flask(__name__)
mysql = MySQL()

config = yaml.safe_load(open('config.conf', 'r'))

application.config['SECRET_KEY'] = config['SECRET_KEY']

application.config['MYSQL_DATABASE_USER'] = config['MYSQL_CONFIG']['MYSQL_DATABASE_USER']
application.config['MYSQL_DATABASE_PASSWORD'] = config['MYSQL_CONFIG']['MYSQL_DATABASE_PASSWORD']
application.config['MYSQL_DATABASE_DB'] = config['MYSQL_CONFIG']['MYSQL_DATABASE_DB']
application.config['MYSQL_DATABASE_HOST'] = config['MYSQL_CONFIG']['MYSQL_DATABASE_HOST']

mysql.init_app(application)


@application.route('/')
def index():
    return redirect('/esv')


@application.route('/esv')
@application.route('/esv/')
def landing():
    preston = Preston(
        user_agent=config['EVE_OAUTH_USER_AGENT'],
        client_id=config['EVE_OAUTH_CLIENT_ID'],
        client_secret=config['EVE_OAUTH_SECRET'],
        callback_url=config['EVE_OAUTH_CALLBACK'],
        scope=config['EVE_OAUTH_SCOPE']
    )
    return render_template('dist/view.html',
                           show_crest=True,
                           crest_url=preston.get_authorize_url(),
                           network_time=0,
                           parse_time=0,
                           base_url=config['BASE_URL'])


@application.route('/esv/view')
@application.route('/esv/view/<refresh_token>')
def view_pilot(refresh_token=None):
    try:
        if refresh_token is None:
            # check response
            if 'error' in request.path:
                flash("There was an error in EVE's response", 'error')
                return redirect(url_for('landing'))

            try:
                preston = Preston(
                    user_agent=config['EVE_OAUTH_USER_AGENT'],
                    client_id=config['EVE_OAUTH_CLIENT_ID'],
                    client_secret=config['EVE_OAUTH_SECRET'],
                    callback_url=config['EVE_OAUTH_CALLBACK'],
                    scope=config['EVE_OAUTH_SCOPE']
                )
                auth = preston.authenticate(request.args['code'])
            except Exception as e:
                print('SSO callback exception: ' + str(e))
                flash('There was an error signing you in.', 'error')
                return redirect(url_for('landing'))

            return redirect(url_for('view_pilot', refresh_token=auth.refresh_token))

        else:
            preston = Preston(
                user_agent=config['EVE_OAUTH_USER_AGENT'],
                client_id=config['EVE_OAUTH_CLIENT_ID'],
                client_secret=config['EVE_OAUTH_SECRET'],
                callback_url=config['EVE_OAUTH_CALLBACK'],
                scope=config['EVE_OAUTH_SCOPE'],
                refresh_token=refresh_token
            )
            pilot_info = preston.whoami()
            pilot_name = pilot_info['CharacterName']
            pilot_id = pilot_info['CharacterID']

    except Exception as e:
        flash('There was an error parsing skills: ' + str(e), 'error')
        return redirect(url_for('landing'))

    return render_template('dist/view.html',
                           show_crest=False,
                           pilot_name=pilot_name,
                           pilot_id=pilot_id,
                           base_url=config['BASE_URL'],
                           refresh_token=refresh_token)


@application.route('/esv/get_skills/<refresh_token>')
def get_skills(refresh_token):
    try:
        conn = mysql.connect()
        cursor = conn.cursor()

    except Exception as e:
        msg = "MySQL Error"
        return get_json_response(e, msg)

    try:
        t0 = time.time()

        preston = Preston(
            user_agent=config['EVE_OAUTH_USER_AGENT'],
            client_id=config['EVE_OAUTH_CLIENT_ID'],
            client_secret=config['EVE_OAUTH_SECRET'],
            callback_url=config['EVE_OAUTH_CALLBACK'],
            scope=config['EVE_OAUTH_SCOPE'],
            refresh_token=refresh_token
        )

        pilot_info = preston.whoami()

    except Exception as e:
        msg = "Authentication Error"
        return get_json_response(e, msg)

    try:
        pilot_id = pilot_info['CharacterID']
        skills_response = preston.get_op('get_characters_character_id_skills', character_id=pilot_id)

        skillqueue_response = preston.get_op('get_characters_character_id_skillqueue', character_id=pilot_id)

        t1 = time.time()

        network_time = t1 - t0

        if skills_response.get('error') is not None:
            raise Exception('ESI error: ' + skills_response.get('error'))

        skills = skills_response['skills']
        skill_ids = [skill.get('skill_id') for skill in skills]

        query = "SELECT typeID, typeName FROM invTypes WHERE invTypes.typeID IN ({})" \
            .format(','.join(str(i) for i in skill_ids))
        cursor.execute(query)
        skill_names = dict(cursor.fetchall())

        query = "SELECT groupName, GROUP_CONCAT(DISTINCT typeID) " \
                "FROM invTypes " \
                "LEFT JOIN invGroups ON invGroups.groupID = invTypes.groupID " \
                "WHERE invTypes.groupID IN " \
                "(SELECT groupID from invGroups where categoryID = {}) " \
                "GROUP BY groupName".format(config['CATEGORY_SKILLS'])
        cursor.execute(query)
        skill_groups = dict(cursor.fetchall())

        skill_groups = {skill_group: skill_ids_csv.split(',') for skill_group, skill_ids_csv in skill_groups.items()}

    except Exception as e:
        msg = "Error fetching skills"
        return get_json_response(e, msg)

    try:
        t0 = time.time()

        skills_stats = {}
        skills_dict = {}

        skills_stats['Totals'] = {}
        skills_stats['Totals']['num_skills'] = len(skills)
        skills_stats['Totals']['total_sp'] = 0

        # Parse skills into dicts for the html response
        for group, child_skills in skill_groups.items():
            child_skill_ints = [int(i) for i in child_skills]
            for skill in skills:
                if skill['skill_id'] in child_skill_ints:
                    # Prevents dict errors by setting child items to {} first
                    if group not in skills_dict:
                        skills_dict[group] = {}
                        skills_stats[group] = {}
                        skills_stats[group]['skills_in_group'] = 0
                        skills_stats[group]['sp_in_group'] = 0

                    # Add skill and metadata to dicts
                    skill_id = skill['skill_id']
                    skill_name = skill_names[skill_id]
                    skill_level_trained = skill['active_skill_level']
                    skills_dict[group][skill_name] = skill_level_trained
                    skills_stats[group]['skills_in_group'] += 1
                    skills_stats[group]['sp_in_group'] += skill['skillpoints_in_skill']
                    skills_stats['Totals']['total_sp'] += skill['skillpoints_in_skill']

    except Exception as e:
        msg = "Error parsing skills"
        return get_json_response(e, msg)

    try:
        utcnow = datetime.utcnow()
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        current_skill = skillqueue_response[0]
        utcnow_fmt = datetime.strftime(utcnow, fmt)
        skill_count = len(skillqueue_response)
        while current_skill['finish_date'] < utcnow_fmt:
            current_skill = skillqueue_response[1]
            skill_count = len(skillqueue_response) - 1
            skillqueue_response.pop(0)

        finish_datetime = datetime.strptime(current_skill['finish_date'], fmt)
        level_start_sp = current_skill['level_start_sp']
        level_end_sp = current_skill['level_end_sp']
        current_sp = next(skill.get('skillpoints_in_skill') for skill in skills if skill.get('skill_id') == current_skill['skill_id'])

        completed_pct = ((current_sp - level_start_sp) / level_end_sp) * 100
        skill_name = skill_names[current_skill['skill_id']]
        current_skill = {
            'finish_datetime': datetime.strftime(finish_datetime, '%Y-%m-%d %H:%M:%S'),
            'completed_pct': completed_pct,
            'skill_name': skill_name,
            'skill_level': current_skill['finished_level']
        }

        total_time = utcnow
        for skill in skillqueue_response:
            total_time += datetime.strptime(skill['finish_date'], fmt) - max(
                datetime.strptime(skill['start_date'], fmt),
                utcnow
            )

        total_time = str(total_time).split('.')[0]

        t1 = time.time()

        parse_time = t1 - t0

    except Exception as e:
        msg = "Error parsing skill queue"
        return get_json_response(e, msg)

    return jsonify({
        'success': True,
        'payload': render_template('dist/ajax.html',
                                   skills=skills_dict,
                                   skills_stats=skills_stats,
                                   network_time=network_time,
                                   parse_time=parse_time,
                                   base_url=config['BASE_URL'],
                                   current_skill=current_skill,
                                   skill_count=skill_count,
                                   total_time=total_time)
    })


def get_json_response(e, msg):
    return jsonify({
        'message': "{}: {}".format(msg, e),
        'success': False
    })


if __name__ == "__main__":
    application.run(host='localhost', debug=True, ssl_context=("localhost.crt", "localhost.key"))
