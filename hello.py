import flask
import flask.views
import os
import functools
import urllib2
import re
import operator
import webbrowser
import sys
from datetime import datetime
from bs4 import BeautifulSoup
#from beautifulsoup4 import BeautifulSoup
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
app = flask.Flask(__name__)
app.secret_key = "bacon"

#redis/background job stuff commented out for now
#import requests
#from rq import Queue
#from worker import conn

#q = Queue(connection=conn)

#users = {'user':'pass'}

class Main(flask.views.MethodView):

    def get(self):
        return flask.render_template('remote.html')

#     def post(self):
#         if 'logout' in flask.request.form:
#             flask.session.pop('username', None)
#             return flask.redirect(flask.url_for('index'))
#         required = ['username', 'passwd']
#         for r in required:
#             if r not in flask.request.form:
#                 flask.flash("Error: {0} is required.".format(r))
#                 return flask.redirect(flask.url_for('index'))
#         username = flask.request.form['username']
#         passwd = flask.request.form['passwd']
#         if username in users and users[username] == passwd:
#             flask.session['username'] = username
#         else:
#             flask.flash("Username doesn't exist or incorrect password")
#         return flask.redirect(flask.url_for('index'))

# def login_required(method):
#     @functools.wraps(method)
#     def wrapper(*args, **kwargs):
#         if 'username' in flask.session:
#             return method(*args, **kwargs)
#         else:
#             flask.flash("A login is required to see the page!")
#             return flask.redirect(flask.url_for('index'))
#     return wrapper

class Remote(flask.views.MethodView):
#     @login_required
    def get(self):
        return flask.render_template('remote.html')

#     @login_required
    def post(self):
        input = flask.request.form['expression']
##        result = q.enqueue(prepare, input)
        result = prepare(input)
##        result = eval(flask.request.form['expression'])
        #flask.flash(result)
        return flask.render_template('remote.html', result=result)

app.add_url_rule('/',
                 view_func=Main.as_view('index'),
                 methods=["GET", "POST"])
app.add_url_rule('/remote/',
                 view_func=Remote.as_view('remote'),
                 methods=['GET', 'POST'])

def prepare(wikiurl):
##    resp = requests.get(wikiurl)
    sys.stdout.flush()
    wikiurl = wikiurl.replace("%", "%25")
    wikiurl = wikiurl.replace("'", "%27")
    wikiurl = wikiurl.replace("&", "%26")
    startTime = datetime.now()
    offset = ""
    matchlist = ""
    matchdict = {}
    monthdict = {}
    totalmatches = 0
    return scrapewiki(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, monthdict)

def scrapewiki(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, monthdict):
    sys.stdout.write("***scrapewiki***\n")
    sys.stdout.flush()
    matchesonpage = 0
    url = "http://en.wikipedia.org/w/index.php?title="+wikiurl+"&offset="+offset+"&limit=500&action=history"
    page = opener.open(url)
    offset = ""

    soup = BeautifulSoup(opener.open(url))
# populate monthdict and matchdict... maybe it would make sense to make monthdict all at once later on, or go directly from matchdict to html table...
    for link in soup.find_all("a", class_="mw-changeslist-date"):
        totalmatches += 1
        stime, sday, smonth, syear = map(str, link.string.split(' '))
        monthlist=["January","February","March","April","May","June","July","August","September","October","November","December"]
        if smonth in monthlist:
            smonth = "%02d" % (monthlist.index(smonth)+1)
        yyyymmdd = str(syear+"-"+smonth+"-"+sday)
        yyyymm2 = str(syear+"-"+smonth)
        if yyyymmdd in matchdict:
            matchdict[yyyymmdd] += 1
        else:
            matchdict[yyyymmdd] = 1
        if yyyymm2 in monthdict:
            monthdict[yyyymm2] += 1
        else:
            monthdict[yyyymm2] = 1
#find offset
    for link in soup.find_all("a", class_="mw-nextlink"):
        offset = link.get('href')
        offset = re.search('offset=(\d{14})', offset).group(1)        
        sys.stdout.write("offset: "+offset+"\n")
#determine if we need to go to next page
    if offset != "":
        sys.stdout.write("***recursion***\n")
        return scrapewiki(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, monthdict)
    else:
        return dumpresults(wikiurl, matchlist, matchdict, totalmatches, startTime, monthdict)

def dumpresults(wikiurl, matchlist, matchdict, totalmatches, startTime, monthdict):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
    maxeditday = max(matchdict.iteritems(), key = operator.itemgetter(1))[0]
    timeTotal = datetime.now()-startTime
    output = "Profiling the "+wikiurl+" page...\nA total of "+str(totalmatches)+" edits have been made to this page\nThe highest number of edits ("+ str(matchdict[maxeditday]) + ') to the <a href="http://en.wikipedia.org/wiki/'+wikiurl+'">'+wikiurl+"</a> page occurred on " + str(maxeditday) + " (dd/mm/yyyy).\n"

    testmonthdict = {}
#maybe build monthdict here so we don't have to pass it around through recursion:
    for key in matchdict:
        myear, mmonth, mday = map(int, key.split('-'))
        newkey = str(myear)+"-"+str(mmonth)
        if newkey in testmonthdict:
            testmonthdict[newkey] += 1
        else:
            testmonthdict[newkey] = 1

    sys.stdout.write("1: "+str(testmonthdict)+"\n")
    sys.stdout.write("2: "+str(monthdict)+"\n")

# this turns monthdict into yeardict so we can make nice horizontal tables
    yeardict = {}

#    sys.stdout.write("monthdict: "+str(monthdict)+"\n")
    for key in monthdict:
        try:
            dyear, dmonth = map(int, key.split('-'))
        except Exception:
            continue
        if dmonth not in range(1,13):
            break
        if dyear not in yeardict:
            yeardict[dyear] = [0]*12
        yeardict[dyear][dmonth-1] = monthdict[key]

    output += 'This code took '+str(timeTotal)+" seconds to execute\n"
    color = max(monthdict.iteritems(),key=operator.itemgetter(1))[0]
    color = monthdict[color]
    maxeditmonth = color
    color = 255/float(color)
# turns yeardict into an html table with colors based on activity
    htmltable = '<table border="1"><tr><td></td><td>Jan</td><td>Feb</td><td>Mar</td><td>Apr</td><td>May</td><td>Jun</td><td>Jul</td><td>Aug</td><td>Sep</td><td>Oct</td><td>Nov</td><td>Dec</td></tr>'    
    for key in yeardict:
        htmltable += '<tr><td>'+str(key)+'</td>'
        for i in range(0,12):
            htmltable += '<td style="background-color:rgba(%i,%i,0,1);">%s</td>' % (yeardict[key][i]*color, (maxeditmonth-yeardict[key][i])*color , str(yeardict[key][i]))
        htmltable += '</tr>'
    htmltable += "</table>"

    output += htmltable
#    sys.stdout.write("Output is: " + output+"\n")
    sys.stdout.write(str(matchdict)+"\n")
    sys.stdout.flush()
    return flask.Markup(output)
    
port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
