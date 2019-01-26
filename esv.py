from datetime import datetime
from flask import Flask, render_template, flash, request, redirect, url_for
import json
from preston_new import Preston
import time
import yaml

application = Flask(__name__)

config = yaml.load(open('config.conf', 'r'))

application.config['SECRET_KEY'] = config['SECRET_KEY']


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
        flash('There was an error parsing skills', 'error')
        print('Skill Parse error: ' + str(e))
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
        print(e)
        return "Error authenticating"

    try:
        pilot_id = pilot_info['CharacterID']
        skills = preston.get_op('get_characters_character_id_skills', character_id=pilot_id)
        if skills.get('error') is not None:
            msg = 'ESI error: ' + skills.get('error')
            print(msg)
            return msg

        skills = skills['skills']

        # Prepare and get names from the skill ids
        ids_list = []
        for skill in skills:
            ids_list.append(skill.get('skill_id'))

    except Exception as e:
        print(e)
        return "Error fetching skills"

    try:

        skill_names = preston.post_op('post_universe_names', path_data=None, post_data=ids_list)

    except Exception as e:
        print(e)
        return "Error fetching skill_names"

    try:
        t1 = time.time()

        network_time = t1 - t0

        t0 = time.time()

        skill_groups = json.load(open('static/json/skill_groups.json', 'r'))

        skills_stats = {}
        skills_dict = {}

        skills_stats['Totals'] = {}
        skills_stats['Totals']['num_skills'] = len(skills)
        skills_stats['Totals']['total_sp'] = 0

        # Parse skills into dicts for the html response
        for group, child_skills in skill_groups.items():
            for skill in skills:
                if skill['skill_id'] in child_skills:
                    # Prevents dict errors by setting child items to {} first
                    if group not in skills_dict:
                        skills_dict[group] = {}
                        skills_stats[group] = {}
                        skills_stats[group]['skills_in_group'] = 0
                        skills_stats[group]['sp_in_group'] = 0

                    # Add skill and metadata to dicts
                    skill_id = skill['skill_id']
                    skill_name = next(
                        item['name'] for item in skill_names if item['id'] == skill_id
                    )
                    skill_level_trained = skill['active_skill_level']
                    skills_dict[group][skill_name] = skill_level_trained
                    skills_stats[group]['skills_in_group'] += 1
                    skills_stats[group]['sp_in_group'] += skill['skillpoints_in_skill']
                    skills_stats['Totals']['total_sp'] += skill['skillpoints_in_skill']

    except Exception as e:
        print(e)
        return "Error parsing skills"

    try:
        skillqueue = preston.get_op('get_characters_character_id_skillqueue', character_id=pilot_id)

        utcnow = datetime.utcnow()
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        current_skill = skillqueue[0]
        utcnow_fmt = datetime.strftime(utcnow, fmt)
        skill_count = len(skillqueue)
        while current_skill['finish_date'] < utcnow_fmt:
            current_skill = skillqueue[1]
            skill_count = len(skillqueue) - 1
            skillqueue.pop(0)

        finish_datetime = datetime.strptime(current_skill['finish_date'], fmt)
        start_datetime = datetime.strptime(current_skill['start_date'], fmt)
        total_time = finish_datetime - start_datetime
        spent_time = utcnow - start_datetime
        time_remaining = total_time - spent_time
        completed_pct = spent_time / total_time * 100
        skill_name = next(
            item['name'] for item in skill_names if item['id'] == current_skill['skill_id']
        )
        current_skill = {
            'time_remaining': str(time_remaining).split('.')[0],
            'finish_datetime': datetime.strftime(finish_datetime, '%Y-%m-%d %H:%M:%S EVE'),
            'completed_pct': completed_pct,
            'skill_name': skill_name,
            'skill_level': current_skill['finished_level']
        }

        total_time = utcnow
        for skill in skillqueue:
            total_time += datetime.strptime(skill['finish_date'], fmt) - max(
                datetime.strptime(skill['start_date'], fmt),
                utcnow
            )

        total_time = str(total_time).split('.')[0]

        t1 = time.time()

        parse_time = t1 - t0

    except Exception as e:
        print(e)
        return "Error parsing skill queue"

    return render_template('dist/ajax.html',
                           skills=skills_dict,
                           skills_stats=skills_stats,
                           network_time=network_time,
                           parse_time=parse_time,
                           base_url=config['BASE_URL'],
                           current_skill=current_skill,
                           skill_count=skill_count,
                           total_time=total_time)


if __name__ == "__main__":
    application.run(host='localhost', debug=True, ssl_context=("localhost.crt", "localhost.key"))
