#! /usr/bin/env python2
# Author: Sotirios Roussis - xtonousou
# Description: Zabbix LLD Template for Bareos. Works via bareos-webui with HTTP and not via bconsole.
# Dependencies: requests
# Usage: python2 bareos.py
# Notes: Backup statuses: js/custom-functions.js
# Tested: Centos 7
# Version: 1.0.0

import requests
from json import dumps


class Bareos(object):

    def __init__(self):
        self.host = '127.0.0.1'
        self.username = 'admin'
        self.password = 'password'
        self.director = 'localhost-dir'
        self.base_url = 'http://{0}/bareos-webui'.format(self.host)
        self.status_map = {
            'e': 'Non-fatal error',
            'E': 'Job terminated in error',
            'f': 'Fatal error',
            'T': 'Terminated normally',
            'R': 'Running',
            'C': 'Created but not yet running',
            'B': 'Blocked',
            'D': 'Verify differences',
            'A': 'Canceled by user',
            'F': 'Waiting on File daemon',
            'S': 'Waiting on the Storage daemon',
            'm': 'Waiting for new media',
            'M': 'Waiting for Mount',
            's': 'Waiting for storage resource',
            'j': 'Waiting for job resource',
            'c': 'Waiting for Client resource',
            'd': 'Waiting for maximum jobs',
            't': 'Waiting for start time',
            'p': 'Waiting for higher priority jobs to finish',
            'a': 'SD despooling attributes',
            'i': 'Doing batch insert file records',
            'I': 'Incomplete Job',
            'L': 'Committing data (last despool)',
            'W': 'Terminated normally with warnings',
            'l': 'Doing data despooling',
            'q': 'Queued waiting for device',
        }
        self.level_map = {
            'd': 'Differential',
            'f': 'Full',
            'i': 'Incremental',
        }

        self.session = requests.Session()
    
    def auth(self):
        headers = {
            'connection': 'close',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'accept-encoding': 'gzip, deflate',
        }
        data = {
            'director': self.director,
            'consolename': self.username,
            'password': self.password,
            'locale': 'en_EN',
            'submit': 'Login',
        }
        url = '{0}/auth/login'.format(self.base_url)
        return self.session.post(url, headers=headers, data=data)
    
    def status(self):
        headers = {
            'connection': 'close',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'accept-encoding': 'gzip, deflate',
            'content-type': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
        }
        params = {
            'data': 'jobs',
            'jobname': 'all',
            'status': 'all',
            'period': 3,
            'sort': 'jobid',
            'order': 'asc',
        }
        url = '{0}/job/getData'.format(self.base_url)
        return self.session.get(url, headers=headers, params=params)
    
    def parse(self, response):
        jobs = {x: 0 for x in set(j['name'] for j in response)}

        array = []
        for job in response:
            name = job['name']
            if not name in jobs:
                continue

            array.append({
                '{#JOB_BYTES}': job['jobbytes'],
                '{#JOB_CLIENT}': job['client'],
                '{#JOB_END_TIME}': job['realendtime'],
                '{#JOB_ID}': job['jobid'],
                '{#JOB_NAME}': name,
                '{#JOB_LEVEL}': self.level_map.get(job['level'].lower()),
                '{#JOB_POOL}': job['poolname'],
                '{#JOB_START_TIME}': job['starttime'],
                '{#JOB_STATUS}': self.status_map.get(job['jobstatus']),
            })

            del jobs[name]
        
        return array

    def main(self):
        r = self.auth()
        if not r.ok:
            raise Exception('Cannot authenticate')
       
        r = self.status()
        if not r.ok:
            raise Exception("Cannot get jobs' status")

        json = r.json()
        if not json:
            raise Exception('Empty JSON response')

        lld = self.parse(json)
        if not lld:
            raise Exception('Cannot parse JSON response')
        
        return lld


if __name__ == '__main__':
    LLD = {
        'data': {
            '{#STATUS}': 'Successful',
            'jobs': [],
        },
    }

    try:
        LLD['data']['jobs'] = Bareos().main()
    except Exception as e:
        LLD['data']['{#STATUS}'] = 'Failed: {0}'.format(e)

    print dumps(LLD)

    exit(0)

