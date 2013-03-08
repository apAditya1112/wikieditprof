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

def prepare(wikiid):
##    resp = requests.get(wikiurl)
    global wikiurl
    wikiurl = wikiid
    wikiurl = wikiurl.replace("%", "%25")
    wikiurl = wikiurl.replace("'", "%27")
    wikiurl = wikiurl.replace("&", "%26")
    startTime = datetime.now()
    offset = ""
    matchlist = ""
    matchdict = {}
    totalmatches = 0
    return scrapewiki(offset, matchlist, matchdict, totalmatches,
                      startTime)

def scrapewiki(offset, matchlist, matchdict, totalmatches, startTime):
    matchesonpage = 0
    url = "http://en.wikipedia.org/w/index.php?title=" + wikiurl + "&offset=" + offset + "&limit=1000&action=history"
    page = opener.open(url)
    offset = ""

    soup = BeautifulSoup(opener.open(url))
# populate monthdict and matchdict... maybe it would make sense to make monthdict all at once later on, or go directly from matchdict to html table...
    for link in soup.find_all("a", class_="mw-changeslist-date"):
        totalmatches += 1
        stime, sday, smonth, syear = map(str, link.string.split(' '))
        monthlist = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        if smonth in monthlist:
            smonth = "%02d" % (monthlist.index(smonth)+1)
        yyyymmdd = str(syear+"-"+smonth+"-"+sday)
        yyyymm2 = str(syear+"-"+smonth)
        if yyyymmdd in matchdict:
            matchdict[yyyymmdd] += 1
        else:
            matchdict[yyyymmdd] = 1
#find offset
    for link in soup.find_all("a", class_="mw-nextlink"):
        offset = link.get('href')
        offset = re.search('offset=(\d{14})', offset).group(1)
#determine if we need to go to next page
    if offset != "":
        return scrapewiki(offset, matchlist, matchdict, totalmatches, startTime)
    else:
        return dumpresults(matchlist, matchdict, totalmatches, startTime)

def dumpresults(matchlist, matchdict, totalmatches, startTime):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
    maxeditday = max(matchdict.iteritems(), key=operator.itemgetter(1))[0]
    timeTotal = datetime.now()-startTime
    datecreated = str(sorted(matchdict)[0])
    output = ""
    output = "Profiling the " + wikiurl + " page...\nA total of " + str(totalmatches) + " edits have been made to this page since it was created on " + datecreated + "\n"
    maxeditdaystr = str(maxeditday).replace("-","")
    output += 'The highest number of edits (' + str(matchdict[maxeditday]) + ') to the <a href="http://en.wikipedia.org/wiki/' + wikiurl + '">' + wikiurl + '</a> page occurred on <a href="http://en.wikipedia.org/w/index.php?title=' + wikiurl + '&offset=' + maxeditdaystr + '000000&limit=' + str(matchdict[maxeditday]) + '&action=history">' + str(maxeditday) + '</a> (dd/mm/yyyy).\n'

    testmonthdict = {}
#build monthdict:
#if i can figure out how to find max edit month and determine colors
#for heat map, I wouldn't need monthdict at all and could go straight
#from matchdict -> yeardict
    for key in matchdict:
        myear, mmonth, mday = map(int, key.split('-'))
        newkey = str(myear)+"-"+str(mmonth)
        if newkey in testmonthdict:
            testmonthdict[newkey] += matchdict[key]
        else:
            testmonthdict[newkey] = matchdict[key]

#go straight from matchdict to yeardict, so we can easily drop monthdict
#in the future
    yeardict2 = {}
    for key in matchdict:
        try:
            dyear, dmonth, dday = map(int, key.split('-'))
        except Exception:
            continue
        if dmonth not in range(1, 13):
            break
        if dyear not in yeardict2:
            yeardict2[dyear] = [0]*12
        yeardict2[dyear][dmonth-1] = matchdict[key]

# this turns monthdict into yeardict so we can make nice horizontal tables
    yeardict = {}
    for key in testmonthdict:
        try:
            dyear, dmonth = map(int, key.split('-'))
        except Exception:
            continue
        if dmonth not in range(1, 13):
            break
        if dyear not in yeardict:
            yeardict[dyear] = [0]*12
        yeardict[dyear][dmonth-1] = testmonthdict[key]
    output += 'This code took '+str(timeTotal)+" seconds to execute\n"
    color = max(testmonthdict.iteritems(), key=operator.itemgetter(1))[0]
    color = testmonthdict[color]
    maxeditmonth = color
    color = 255/float(color)
# turns yeardict into an html table with colors based on activity
    htmltable = '<table border="1" style="width:100%; border-collapse:collapse; border-width:0px;"><tr><td></td><td>Jan</td><td>Feb</td><td>Mar</td><td>Apr</td><td>May</td><td>Jun</td><td>Jul</td><td>Aug</td><td>Sep</td><td>Oct</td><td>Nov</td><td>Dec</td></tr>'
    for key in yeardict2:
        htmltable += '<tr><td>'+str(key)+'</td>'
        for i in range(0, 12):
            if yeardict[key][i] == 0:
                htmltable += '<td style="background-color:rgba(235,235,235,1);">%s</td>' % (str(yeardict[key][i]))
            else:
                htmltable += '<td style="background-color:rgba(%i,%i,0,1);"><a href="http://en.wikipedia.org/w/index.php?title=%s&offset=%s%s00000000&limit=%s&action=history">%s</a></td>' % (yeardict[key][i]*color, (maxeditmonth-yeardict[key][i])*color, wikiurl, str(key), str(i+1), str(yeardict[key][i]), str(yeardict[key][i]))
        htmltable += '</tr>'
    htmltable += "</table>"

    output += htmltable
    return flask.Markup(output)

port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
