import csv
import datetime
import os
import requests

REVCONTENT_API = 'https://api.revcontent.io'



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

    def fetch(self, method, url, **kwargs):
        """
        TODO: Handle expired access token, re-login on expire
        """
        HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
        method = method.strip().upper()

        if method.strip().upper() not in HTTP_METHODS:
            raise ValueError('Invalid Http Method: {}'.format(method))

        return requests.request(method, url, **kwargs)

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
                              data=payload)
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
        if date_from is None and date_to is None:
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
widget_file = open('widget_stats_yesterday_{}.csv'.format(today), 'w')
csvwriter = csv.writer(widget_file)

yesterday = datetime.date.today() - datetime.timedelta(1)
yesterday_string = yesterday.strftime('%Y-%m-%d')


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
