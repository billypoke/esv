# EVE ESI Skill Viewer

## What is this?

A web app to view your skills, grouped into useful categories. See where you have good coverage, and where you need to 
train your skills.

## How does it work?

Using [EVE's SSO](https://community.eveonline.com/news/dev-blogs/eve-online-sso-and-what-you-need-to-know/) 
(Single Sign On) system and the new [ESI API](https://esi.tech.ccp.is/latest/). You are guaranteed to be going to CCP's 
server for authentication, and you can see exactly what permissions you are granting to this application.

## Installation

Python 3.x is required.

1. `pip install -r requirements.txt`
2. Copy `config.conf.default` to `config.conf`
3. Go to https://developers.eveonline.com/ and create a new application
4. Choose a name and write a description
5. For 'Connection Type', choose `Authentication & API Access`
6. The required scopes are listed in `config.conf.deafult` but are `publicData` & `esi-skills.read_skills.v1`
7. The Callback URL is where the SSO system will redirect your users after authentication. It should end in 
`/statschecker/view` for this application
8. Copy the information for your app into `config.conf`
9. Run `python wsgi.py`
