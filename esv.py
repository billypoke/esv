import json

import requests
import time
import yaml
from flask import Flask, render_template, flash, request, redirect, url_for
from preston.esi import Preston

application = Flask(__name__)

names_url = 'https://esi.tech.ccp.is/latest/universe/names/?datasource=tranquility'
config = yaml.load(open('config.conf', 'r'))

application.config['SECRET_KEY'] = config['SECRET_KEY']

preston = Preston(
    user_agent=config['EVE_OAUTH_USER_AGENT'],
    client_id=config['EVE_OAUTH_CLIENT_ID'],
    client_secret=config['EVE_OAUTH_SECRET'],
    callback_url=config['EVE_OAUTH_CALLBACK'],
    scope=config['EVE_OAUTH_SCOPE']
)


@application.route('/esv')
@application.route('/esv/')
def landing():
    return render_template('dist/view.html', show_crest=True, crest_url=preston.get_authorize_url(), network_time=0,
                           parse_time=0, base_url=config['BASE_URL'])


@application.route('/esv/view')
@application.route('/esv/view/<refresh_token>')
def view_pilot(refresh_token=None):
    try:
        if refresh_token is None:
            # check response
            if 'error' in request.path:
                flash('There was an error in EVE\'s response', 'error')
                return redirect(url_for('landing'))

            try:
                auth = preston.authenticate(request.args['code'])
            except Exception as e:
                print('SSO callback exception: ' + str(e))
                flash('There was an authentication error signing you in.', 'error')
                return redirect(url_for('landing'))

            return redirect(url_for('view_pilot', refresh_token=auth.refresh_token))

        else:
            auth = preston.use_refresh_token(refresh_token)
            pilot_info = auth.whoami()
            pilot_name = pilot_info['CharacterName']
            pilot_id = pilot_info['CharacterID']

    except Exception as e:
        flash('There was an error parsing skills', 'error')
        print('Skill Parse error: ' + str(e))
        return redirect(url_for('landing'))

    return render_template('dist/view.html', show_crest=False, pilot_name=pilot_name, pilot_id=pilot_id,
                           base_url=config['BASE_URL'], refresh_token=refresh_token)


@application.route('/esv/get_skills/<refresh_token>')
def get_skills(refresh_token):
    t0 = time.time()
    auth = preston.use_refresh_token(refresh_token)
    pilot_info = auth.whoami()
    pilot_id = pilot_info['CharacterID']
    result = auth.characters[pilot_id].skills()
    if result.get('error') is not None:
        print('ESI error: ' + result.get('error'))
        flash('ESI is not responding. Please try again, or wait a few minutes.', 'error')
        return redirect(url_for('landing'))

    skills = result['skills']

    # Prepare and get names from the skill ids
    ids_list = []
    for skill in skills:
        ids_list.append(skill.get('skill_id'))

    try:
        skill_names = requests.post(url=names_url, json=ids_list).json()

    except Exception as e:
        flash('There was an error in EVE\'s response', 'error')
        print('SSO callback exception: ' + str(e))
        return redirect(url_for('landing'))

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
                    item['name'] for item in skill_names if item['id'] == skill_id  # stackoverflow FTW
                )
                skill_level_trained = skill['active_skill_level']
                skills_dict[group][skill_name] = skill_level_trained
                skills_stats[group]['skills_in_group'] += 1
                skills_stats[group]['sp_in_group'] += skill['skillpoints_in_skill']
                skills_stats['Totals']['total_sp'] += skill['skillpoints_in_skill']

    t1 = time.time()

    parse_time = t1 - t0

    return render_template('dist/ajax.html', skills=skills_dict, skills_stats=skills_stats, network_time=network_time,
                           parse_time=parse_time, base_url=config['BASE_URL'])


if __name__ == "__main__":
    application.run(host='0.0.0.0', debug=True, ssl_context='adhoc')
