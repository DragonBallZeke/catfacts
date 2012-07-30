import urllib
import urllib2
import yaml
import json
import twilio.twiml
from twilio.rest import TwilioRestClient
from shove import Shove
from flask import (
        Flask,
        request,
        abort,
        redirect,
        render_template,
        )
from random import choice


class CatFactsREST(object):

    def __init__(self, config):
        self.config = config
        self.apikeys = [s.strip() for s in self.config['apikeys'].split(',')]
        dburi = self.config['dburi']
        self.db = Shove(dburi)
        self.app = Flask(__name__)
        self.api = TwilioRestClient(
                self.config['SID'],
                self.config['token'])
        if 'numbers' not in self.db:
            self.db['numbers'] = []
        f = file('catfacts.raw')
        facts = f.read().split("\n")
        self.db['fact'] = facts
        self.db.sync()

        self.routes = {
                "/api/numbers": (self.add_number, {"methods": ['POST']}),
                "/api/numbers/<num>": (self.remove_number, {"methods":
                    ['DELETE']}),
                "/api/callback": (self.twilio_callback, {"methods": ['POST']}),
                "/api/facts": (self.add_facts, {"methods": ['POST']}),
                "/": (self.view_home, {"methods": ['GET']}),
                "/subscribe": (self.subscribe, {"methods": ['POST']}),
                "/submit": (self.submit, {"methods": ['POST']}),
                }
        map(
            lambda route: self.app.route(route,
                **self.routes[route][1])(self.routes[route][0]),
            self.routes)

    def view_home(self):
        """
        View the CatFacts homepage, where you can submit CatFacts!
        """
        return render_template('index.html')

    def subscribe(self):
        """
        Add a phone number to the CatFacts database.
        """
        number = request.values['number']
        data = json.dumps(dict(
            number=number,
            apikey='key1',
        ))
        payload = dict(json=data)
        print "calling api"
        try:
            print urllib2.urlopen('http://localhost:{0}/api/numbers'.format(
                self.config['_port']), data=urllib.urlencode(payload)).readlines()
        except Exception as e:
            print e
        return redirect('/')  # TODO: Add success message

    def submit(self):
        """
        Submit a cat fact to the CatFacts database.
        """
        fact = request.values['fact']
        data = json.dumps(dict(
            fact=fact,
            apikey='submitkey',
        ))
        payload = dict(json=data)
        print "calling API"
        print urllib2.urlopen('http://localhost:{0}/api/facts'.format(
            self.config['_port']), data=urllib.urlencode(payload)).readlines()
        return redirect('/')  # TODO: Add success message

    def add_number(self):
        """
        POST: /api/numbers
        """
        print "Adding numbers"
        try:
            j = request.values['json']
            data = json.loads(j)
        except Exception as e:
            return json.dumps(dict(
                success=False,
                message="Invalid data recieved"))
        try:
            if data['apikey'] not in self.apikeys:
                raise Exception
        except:
            return json.dumps(dict(
                succes=False,
                message="Unauthorized"))
        try:
            number = data['number']
            print number
            print self.db['numbers']
            if number not in self.db['numbers']:
                self.db['numbers'].append(number)
                print "number added"
                self.db.sync()
                try:
                    print self.api.sms.messages.create(
                        to=number,
                        from_="2037947419",
                        body="Congrats, you have been signed up for catfacts, the Premire cat information service, you will receive hourly cat information")
                    print self.api.sms.messages.create(
                            to=number,
                            from_="2037947419",
                            body=choice(self.db['facts']))
                except Exception as e:
                    print e
                print "message sent"
                return json.dumps(dict(
                    success=True,
                    message="Added {0} to catfacts".format(number)))
            else:
                return json.dumps(dict(
                    success=False,
                    message="{0} is already signed up for catfacts".format(
                            number)))

        except KeyError:
            return json.dumps(dict(
                success=False,
                message="Not Enough paramters"))

    def remove_number(self, num):
        """
        DELETE: /api/numbers/<number>
        """
        if num in self.db:
            self.db['numbers'].remove(num)
            self.db.sync()
            return json.dumps(dict(
                success=True,
                message="Removed {0} from catfacts".format(num)))
        else:
            return json.dumps(dict(
                success=False,
                message="{0} is not signed up for catfacts".format(num)))

    def twilio_callback(self):
        """
        POST: /api/callback
        """
        print "Calling wilio callback"
        response = twilio.twiml.Response()
        response.sms(choice(self.db['facts']))
        print response
        return str(response)

    def add_facts(self):
        """
        POST: /api/facts
        """
        try:
            data = json.loads(request.values['json'])
        except:
            return json.dumps(dict(
                success=False,
                message="Invalid data recieved"))
        try:
            if data['apikey'] not in self.apikeys:
                raise Exception
        except:
            return json.dumps(dict(
                success=False,
                message="Unauthorized"))

        try:
            self.db['facts'].extend(data['facts'])
            self.db.sync()
            return json.dumps(dict(
                success=True,
                message='Added more cat facts'))
        except KeyError:
            return json.dumps(dict(
                success=False,
                message="not enough parameters"))

    def start(self):
        self.app.run(
                host=self.config['host'],
                port=self.config['port'],
                debug=True)

def create(globalArgs, **localArgs):
    app = CatFactsREST(globalArgs)
    app.debug = True
    return app.app

def load_facts(config):
    import requests
    from bs4 import BeautifulSoup
    db = Shove(config['dburi'])
    db['facts'] = []
    url1 = 'http://www.cats.alpha.pl/facts.htm'
    raw = requests.get(url1).text
    soup = BeautifulSoup(raw).findAll('ul')[1]
    for string in soup.stripped_strings:
        if string:
            db['facts'].append(string)
    db.sync()


def cron(config):
    account_sid = config.get("app:main", "SID")
    auth_token = config.get("app:main", "token")
    client = TwilioRestClient(account_sid, auth_token)
    db = Shove(config.get("app:main", "dburi"))
    from_number = config.get("app:main", "from")
    for number in db['numbers']:
        while True:
            fact = choice(db['facts'])
            if len(fact) < 140:
                try:
                    client.sms.messages.create(
                            to=number,
                            from_=from_number,
                            body=fact)
                    print "Sent '{0}' to {1}".format(fact, number)
                    break
                except:
                    print "Failed to send fact to {0}".format(number)

def dump(config):
    db = Shove(config.get("app:main", "dburi"))
    import pprint
    pprint.pprint(db['numbers'])
    pprint.pprint(db['facts'])

def main():
    from sys import argv
    from ConfigParser import ConfigParser
    config = ConfigParser()
    config.read(argv[2])
    if argv[1] == "load":
        load_facts(config)
    elif argv[1] == "cron":
        cron(config)
    elif argv[1] == "dump":
        dump(config)
