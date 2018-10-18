import base64
import csv
import datetime
import os
import time

import requests
import sendgrid
from sendgrid.helpers.mail import Content, Email, Mail, Attachment

REVCONTENT_API = 'https://api.revcontent.io'
RETRY = 5



class RevcontentException(Exception):
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def __str__(self):
        return '{0}:  {1}'.format(self.status_code, self.text)


class Revcontent(object):
    def __init__(self, client_id, client_secret, grant_type='client_credentials'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = grant_type
        self.token = None
        self.headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
        }

    def fetch(self, method, url, retry=True, **kwargs):
        """
        TODO: Handle expired access token, re-login on expire
        """
        HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
        method = method.strip().upper()

        if method.strip().upper() not in HTTP_METHODS:
            raise ValueError('Invalid Http Method: {}'.format(method))

        for attempt in range(RETRY):
            response = requests.request(method, url, **kwargs)
            if not retry:
                break

            if response.json().get('data') is not None:
                break
            else:
                # Print response and wait 5 seconds
                print("Missing data for response['data']")
                print(response.json())
                time.sleep(5)

        return response

    def login(self):
        """ POST https://api.revcontent.io/oauth/token """
        print('logging in...')
        if self.token is None:
            self.headers['Content-Type'] = 'application/x-www-form-urlencode'
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': self.grant_type,
            }
            resp = self.fetch('POST', REVCONTENT_API + '/oauth/token',
                              retry=False, data=payload)
            if resp.status_code == 200:
                data = resp.json()
                self.token = data['access_token']
                print('logged in!')
                self.headers.update({
                    'Authorization': 'Bearer {}'.format(self.token),
                    'Content-Type': 'application/json',
                })
            else:
                logger.error('Failed to get Revcontent access token.')
                raise RevcontentException(resp.status_code, resp.text)

    def get_brand_targets(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/boosts/brands """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/boosts/brands',
                          headers=self.headers)

    def get_topic_targets(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/boosts/targets """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/boosts/targets',
                          headers=self.headers)

    def get_boosts(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/boosts """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/boosts',
                          headers=self.headers).json()

    def get_countries(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/countries """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/countries',
                          headers=self.headers)

    def get_devices(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/devices """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/devices',
                          headers=self.headers)

    def get_languages(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/languages """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/languages',
                          headers=self.headers)

    def get_interests(self):
        """ GET https://api.revcontent.io/stats/api/v1.0/interests """
        return self.fetch('GET', REVCONTENT_API + '/stats/api/v1.0/interests',
                          headers=self.headers)

    def get_widgets(self, date_from, date_to):
        """ GET https://api.revcontent.io/stats/api/v1.0/widgets """
        url = (REVCONTENT_API, '/stats/api/v1.0/widgets?date_from=',
               date_from, '&date_to=', date_to, '&aggregate=yes')
        return self.fetch('GET', ''.join(url), headers=self.headers)

    def get_widgets_stats(self, boost_id, date_from=None):
        """ GET https://api.revcontent.io/stats/api/v1.0/boosts/:boost_id/widgets/stats """
        if date_from is None:
            url = (REVCONTENT_API, '/stats/api/v1.0/boosts/', boost_id,
                   '/widgets/stats?limit=1000&min_spend=1')
        else:
            url = (REVCONTENT_API, '/stats/api/v1.0/boosts/', boost_id,
                   '/widgets/stats?limit=1000&min_spend=1&date_from=',
                   date_from)
        return self.fetch('GET', ''.join(url), headers=self.headers).json()


REVCONTENT_CLIENT_ID = os.environ['REVCONTENT_CLIENT_ID']
REVCONTENT_CLIENT_SECRET = os.environ['REVCONTENT_CLIENT_SECRET']
rev = Revcontent(REVCONTENT_CLIENT_ID, REVCONTENT_CLIENT_SECRET)
rev.login()

# Get all the boosts (aka utm_sources)
boosts_data = rev.get_boosts()
today = datetime.datetime.now().strftime("%Y%m%d_%H%M")
widget_filename = 'widget_stats_yesterday_{}.csv'.format(today)
widget_file = open(widget_filename, 'w')
csvwriter = csv.writer(widget_file)

yesterday = datetime.date.today() - datetime.timedelta(1)
yesterday_string = yesterday.strftime('%Y-%m-%d')

# Generate CSV
header_printed = False
for boost in boosts_data['data']:
    utm_source = boost['utm_codes'].split('&')[0].split('=')[-1]
    print(utm_source)
    # For MTD
    # widget_stats = rev.get_widgets_stats(boost['id'])
    # For yesterday
    widget_stats = rev.get_widgets_stats(boost['id'],
                                         date_from=yesterday_string)

    for widget_stat in widget_stats['data']:
      if not header_printed:
          csvwriter.writerow(['utm_source'] + list(widget_stat.keys()))
          header_printed = True
      csvwriter.writerow([utm_source] + list(widget_stat.values()))

# Close file
widget_file.close()

# Send email via sendgrid
sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
from_email = Email(os.environ.get('SENDGRID_SEND_FROM_EMAIL'),
                   os.environ.get('SENDGRID_SEND_FROM_NAME'))
subject = "Revcontent - Daily Stats"
to_email = Email(os.environ.get("SENDGRID_SEND_TO_EMAIL"))
content = Content("text/plain", "Here is the daily revcontent widget stats")

# Generate attachment
with open(widget_filename, 'rb') as f:
    data = f.read()
    f.close()

encoded = base64.b64encode(data).decode()
attachment = Attachment()
attachment.content = encoded
attachment.type = "text/csv"
attachment.filename = widget_filename
attachment.disposition = "attachment"
attachment.content_id = widget_filename

mail = Mail(from_email, subject, to_email, content)
mail.add_attachment(attachment)

response = sg.client.mail.send.post(request_body=mail.get())
print(response.status_code)
print(response.body)
print(response.headers)
