#!/usr/bin/env python
import exceptions
import json
import sys, re, string, os, tempfile, random
import MySQLdb as mdb
from flask import Flask, jsonify
from string import Template

DBHOST='dbmaster.infra.ring.nlnog.net'
DBUSER='ring'
DBPASS=''
DB='ring'
ERROR=None

def set_error(errmsg=None):
    global ERROR
    if errmsg:
        ERROR=errmsg
    else:
        ERROR=None

def reset_error():
    set_error(None)

def get_error():
    if ERROR:
        return ERROR
    return None

def dbconnect():
    try:
        conn = mdb.connect(host=DBHOST,user=DBUSER,passwd=DBPASS,db=DB,connect_timeout=30)
        return conn
    except mdb.OperationalError as err:
        set_error("Error connecting to database: %s" % err)
        return

def dbclose(conn):
    try:
        conn.close()
    except mdb.OperationalError as err:
        return

def dbquery(conn, q, v=None):
    try:
        cur = conn.cursor(mdb.cursors.DictCursor)
        if v:
            cur.execute(q, v)
        else:
            cur.execute(q)
        for row in cur.fetchall():
            yield row
    except mdb.OperationalError as err:
        set_error("Error in database connection: %s" % err)
        return
    except AttributeError as err:
        set_error("Error in database connection: %s" % err)
        return

def dbget_participants(dbconn=None):
    pl = []
    
    conn = dbconn
    if not dbconn:
        conn = dbconnect()
    query = "select * from participants where public!=0 or public is null"
    res = list(dbquery(conn,query))
    if not dbconn:
        dbclose(conn)

    if get_error():
        return
    try:
        for p in res:
            pl.append({'id':p['id'], 
                       'company':p['company'],
                       'description':p['companydesc'],
                       'url':p['url']
                      })
    except KeyError as err:
        set_error("Key %s not found in database" % err)
        return
    random.shuffle(pl)
    return pl

def dbget_participantid(owner,dbconn=None):
    conn = dbconn
    if not dbconn:
        conn = dbconnect()
    query = "select participant from users where id=%s" % (owner)
    res = list(dbquery(conn,query))
    if not dbconn:
        dbclose(conn)

    if get_error():
        return
    try:
        for u in res:
            return u['participant']
    except KeyError as err:
        set_error("Key %s not found in database" % err)
        return
    return null

def dbget_nodes(dbconn=None):
    nl = []

    conn = dbconn
    if not dbconn:
        conn = dbconnect()
    query = "select * from machines"
    res = list(dbquery(conn,query))
    if get_error():
        return
    try:
        for n in res:
            participant = dbget_participantid(n['owner'],conn)
            if get_error():
                return
            nl.append({'id':n['id'], 
                       'hostname':n['hostname'],
                       'ipv4':n['v4'],
                       'ipv6':n['v6'],
                       'asn':n['autnum'],
                       'countrycode':n['country'],
                       'statecode':n['state'],
                       'city':n['city'],
                       'datacenter':n['dc'],
                       'geo':n['geo'],
                       'active':n['active'],
                       'participant':participant
                      })
    except KeyError as err:
        set_error("Key %s not found in database" % err)
        if not dbconn:
            dbclose(conn)
        return
    if not dbconn:
        dbclose(conn)
    
    random.shuffle(nl)
    return nl

def dbget_countrycodes(dbconn=None):
    cl = []
    
    conn = dbconn
    if not dbconn:
        conn = dbconnect()
    query = "select distinct country from machines where country <>''"
    res = list(dbquery(conn,query))
    if not dbconn:
        dbclose(conn)

    if get_error():
        return
    try:
        for c in res:
            cl.append(c['country'])
    except KeyError as err:
        set_error("Key %s not found in database" % err)
        return
    cl = sorted(cl)
    return cl

def dbget_statecodes(dbconn=None):
    sl = []
    
    conn = dbconn
    if not dbconn:
        conn = dbconnect()
    query = "select distinct state,country from machines where country<>'' and state<>''"
    res = list(dbquery(conn,query))
    if not dbconn:
        dbclose(conn)

    if get_error():
        return
    try:
        for s in res:
            sl.append({'statecode':s['state'],
                       'countrycode':s['country'] 
                      })
    except KeyError as err:
        set_error("Key %s not found in database" % err)
        return
    sl = sorted(sl)
    return sl

def mk_json(results=None,count=None,errormsg=None):
    if not results:
        if not errormsg:
            errormsg='Unable to retrieve results from database'
        return jsonify({'info':{'success':0,'errormessage':errormsg}})
    else:
        return jsonify({'info':{'success':1,'resultcount':count},
                        'results':results}
                      )

# Application routing
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, World!"

@app.route('/1.0', methods = ['GET'])
def get_api_1_0():
    api = {
        'participants':'List of participants',
        'participants/[id]':'Participant by id',
        'nodes':'List of nodes',
        'nodes/[id]':'Node by id',
        'nodes/hostname/[hostname]':'Node by hostname',
        'nodes/country/[countrycode]':'Nodes by country',
        'nodes/country/[countrycode]/state/[statecode]':'Nodes by country/state',
        'nodes/active':'Active nodes',
        'nodes/active/country/[countrycode]':'Active nodes by country',
        'nodes/active/country/[countrycode]/state/[statecode]':'Active nodes by country/state',
        'participants/[id]/nodes':'Nodes by participant id',
        'participants/[id]/nodes/active':'Active nodes by participant id',
        'countries':'List of countries',
        'countries/[id]/states':'Statecodes by country',
    }
    return jsonify(api)

@app.route('/1.0/participants', methods = ['GET'])
def get_participants():
    reset_error()
    participantlist = dbget_participants()
    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'participants':participantlist},
                   count=len(participantlist)
                  )

@app.route('/1.0/participants/<int:participant_id>', methods = ['GET'])
def get_participant(participant_id):
    reset_error()
    participantlist = dbget_participants()
    try:
        participantlist = filter(lambda p: p['id'] == participant_id, participantlist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'participants':participantlist},
                   count=len(participantlist)
                  )

@app.route('/1.0/participants/<int:participant_id>/nodes', methods = ['GET'])
def get_nodes_participant(participant_id):
    reset_error()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['participant'] == participant_id, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/participants/<int:participant_id>/nodes/active', methods = ['GET'])
def get_nodes_participant_active(participant_id):
    reset_error()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['participant'] == participant_id, nodelist)
        nodelist = filter(lambda n: n['active'] == 1, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes', methods = ['GET'])
def get_nodes():
    reset_error()
    nodelist = dbget_nodes()
    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/<int:node_id>', methods = ['GET'])
def get_node(node_id):
    reset_error()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['id'] == node_id, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/hostname/<string:node_hostname>', methods = ['GET'])
def get_node_by_name(node_hostname):
    reset_error()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['hostname'] == node_hostname, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/country/<string:country>', methods = ['GET'])
def get_nodes_country(country):
    reset_error()
    country = country.upper()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['countrycode'] == country, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/country/<string:country>/state/<string:state>', methods = ['GET'])
def get_nodes_country_state(country,state):
    reset_error()
    country = country.upper()
    state = state.upper()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['countrycode'] == country, nodelist)
        nodelist = filter(lambda n: n['statecode'] == state, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/active', methods = ['GET'])
def get_nodes_active():
    reset_error()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['active'] == 1, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/active/country/<string:country>', methods = ['GET'])
def get_nodes_active_country(country):
    reset_error()
    country = country.upper()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['active'] == 1, nodelist)
        nodelist = filter(lambda n: n['countrycode'] == country.upper(), nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/nodes/active/country/<string:country>/state/<string:state>', methods = ['GET'])
def get_nodes_active_country_state(country,state):
    reset_error()
    country = country.upper()
    state = state.upper()
    nodelist = dbget_nodes()
    try:
        nodelist = filter(lambda n: n['active'] == 1, nodelist)
        nodelist = filter(lambda n: n['countrycode'] == country, nodelist)
        nodelist = filter(lambda n: n['statecode'] == state, nodelist)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)

    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'nodes':nodelist},count=len(nodelist))

@app.route('/1.0/countries', methods = ['GET'])
def get_countrycodes():
    reset_error()
    countrylist = dbget_countrycodes()
    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'countrycodes':countrylist},count=len(countrylist))

@app.route('/1.0/countries/<string:country>/states', methods = ['GET'])
def get_statecodes(country):
    reset_error()
    country = country.upper()
    countrylist = dbget_statecodes()
    try:
        countrylist = filter(lambda c: c['countrycode'] == country, countrylist)
        statelist = []
        for line in countrylist:
            for k,v in line.iteritems():
                if k=='statecode':
                    statelist.append(v)
    except TypeError:
        pass
    except KeyError as err:
        set_error("Filter key %s not found" % err)
    
    if get_error():
        return mk_json(errormsg=set_error())
    return mk_json(results={'statecodes':statelist},count=len(statelist))

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)

