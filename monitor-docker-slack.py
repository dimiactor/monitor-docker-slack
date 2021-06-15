#!/usr/bin/python
# -------------------------------------------------------------------
# @copyright 2017 DennyZhang.com
# Licensed under MIT
#   https://www.dennyzhang.com/wp-content/mit_license.txt
#
# File : monitor-docker-slack.py
# Author : Denny <https://www.dennyzhang.com/contact>
# Description :
# --
# Created : <2017-08-20>
# Updated: Time-stamp: <2017-11-13 11:00:53>
# -------------------------------------------------------------------
import argparse
import json
import re
import time

import requests_unixsocket
import requests


def name_in_list(name, name_pattern_list):
    for name_pattern in name_pattern_list:
        if re.search(name_pattern, name) is not None:
            return True
    return False


################################################################################

def list_containers_by_sock(docker_sock_file):
    session = requests_unixsocket.Session()
    container_list = []
    socket = docker_sock_file.replace("/", "%2F")
    url = "http+unix://%s/%s" % (socket, "containers/json?all=1")
    r = session.get(url)
    # TODO: error handling
    assert r.status_code == 200
    for container in json.loads(r.content):
        item = (container["Names"], container["Status"])
        container_list.append(item)
    return container_list


def get_stopped_containers(container_list):
    return [container for container in container_list if 'Exited' in container[1]]


def get_unhealthy_containers(container_list):
    return [container for container in container_list if 'unhealthy' in container[1]]


# TODO: simplify this by lambda
def containers_remove_by_name_pattern(container_list, name_pattern_list):
    if len(name_pattern_list) == 0:
        return container_list

    l = []
    for container in container_list:
        names, status = container
        for name in names:
            if name_in_list(name, name_pattern_list):
                break
        else:
            l.append(container)
    return l


def container_list_to_str(container_list):
    msg = ""
    for container in container_list:
        names, status = container
        msg = f"{names}: {status}\n{msg}"
    return msg


def monitor_docker_slack(docker_sock_file, white_pattern_list):
    container_list = list_containers_by_sock(docker_sock_file)
    stopped_container_list = get_stopped_containers(container_list)
    unhealthy_container_list = get_unhealthy_containers(container_list)

    stopped_container_list = containers_remove_by_name_pattern(stopped_container_list, white_pattern_list)
    unhealthy_container_list = containers_remove_by_name_pattern(unhealthy_container_list, white_pattern_list)

    err_msg = ""
    if len(stopped_container_list) != 0:
        err_msg = "Detected Stopped Containers: \n%s\n%s" % (container_list_to_str(stopped_container_list), err_msg)
    if len(unhealthy_container_list) != 0:
        err_msg = "Detected Unhealthy Containers: \n%s\n%s" % (container_list_to_str(unhealthy_container_list), err_msg)

    if err_msg == "":
        return "OK", "OK: detect no stopped or unhealthy containers"
    else:
        return "ERROR", err_msg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--slack_webhook', required=True, help="Slack webhook to post alerts.", type=str)
    parser.add_argument('--whitelist', default='', required=False,
                        help="Skip checking certain containers. A list of regexp separated by comma.", type=str)
    parser.add_argument('--check_interval', default='300', required=False, help="Periodical check. By seconds.",
                        type=int)
    parser.add_argument('--msg_prefix', default='', required=False, help="Slack message prefix.", type=str)
    l = parser.parse_args()
    check_interval = l.check_interval
    white_pattern_list = l.whitelist.split(',')

    if white_pattern_list == ['']:
        white_pattern_list = []

    slack_webhook = l.slack_webhook
    msg_prefix = l.msg_prefix

    if slack_webhook == '':
        print("Warning: Please provide slack webhook, to receive alerts properly.")

    requests.post(slack_webhook, data=json.dumps({'text': 'Hello Channel! I am watching now!'}))

    # TODO
    slack_username = "@denny"

    has_send_error_alert = False
    while True:
        (status, err_msg) = monitor_docker_slack("/var/run/docker.sock", white_pattern_list)
        if msg_prefix != "":
            err_msg = "%s\n%s" % (msg_prefix, err_msg)
        print("%s: %s" % (status, err_msg))
        if status == "OK":
            if has_send_error_alert is True:
                requests.post(slack_webhook, data=json.dumps({'text': err_msg}))
                has_send_error_alert = False
        else:
            if has_send_error_alert is False:
                requests.post(slack_webhook, data=json.dumps({'text': err_msg}))
                # avoid send alerts over and over again
                has_send_error_alert = True
        time.sleep(check_interval)
# File : monitor-docker-slack.py ends

