import flask
import flask.views
import os
import functools
import re
import operator
import webbrowser
import sys
import requests
#import MySQLdb
#import sqlite3
from flask import g
from datetime import datetime
from bs4 import BeautifulSoup

app = flask.Flask(__name__)
app.secret_key = "bacon"

#redis/background job stuff commented out for now
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
#not totally sure this works:
#    wikiurl = urllib2.quote(wikiurl)
    startTime = datetime.now()
    offset = ""
    matchlist = ""
    matchdict = {}
    totalmatches = 0
    return scrapewiki(offset, matchlist, matchdict, totalmatches, startTime)

def scrapewiki(offset, matchlist, matchdict, totalmatches, startTime):
    matchesonpage = 0
    global numrequests
    numrequests = 50
    url = "http://en.wikipedia.org/w/index.php?title=" + wikiurl + "&offset=" + offset + "&limit=" + str(numrequests) + "&action=history"
    page = requests.get(url)
    offset = ""

    soup = BeautifulSoup(page.text)
# populate matchdict
    for link in soup.find_all("a", class_="mw-changeslist-date"):
        totalmatches += 1
        print link.string
        stime, sday, smonth, syear = map(str, link.string.split(' '))
        yyyymmdd = datetime.strptime(syear+"-"+smonth+"-"+sday, '%Y-%B-%d')
        if yyyymmdd in matchdict:
            matchdict[yyyymmdd] += 1
            for span in soup.find_all("span", class_="mw-plusminus-neg"):
#                print span.string
                sys.stdout.write(span.string)
#            matchdict[yyyymmddsize] += pagedelta
        else:
            matchdict[yyyymmdd] = 1
#experimental: track change in page size
#    for span in soup.find_all("span", {"class" : re.compile('mw-plusminus-.*')}):
#        sys.stdout.write(span.string)


#find offset
    for link in soup.find_all("a", class_="mw-nextlink"):
        offset = link.get('href')
        offset = re.search('offset=(\d{14})', offset).group(1)
#determine if we need to go to next page
    if offset != "":
#        sys.stdout.write("\n"+str((datetime.now()-startTime).total_seconds())+"\n")
        if (datetime.now()-startTime).total_seconds() > 25:
            return dumpresults(matchlist, matchdict, totalmatches, startTime)
        else:
            return scrapewiki(offset, matchlist, matchdict, totalmatches, startTime)
    if totalmatches == 0:
        return flask.Markup("That does not appear to be an extant Wikipedia page. Please try again.")
    else:
        return dumpresults(matchlist, matchdict, totalmatches, startTime)

def dumpresults(matchlist, matchdict, totalmatches, startTime):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
    maxeditday = max(matchdict.iteritems(), key=operator.itemgetter(1))[0]
    timeTotal = datetime.now()-startTime
    datecreated = sorted(matchdict)[0]
    output = ""
#    output += "Profiling the " + wikiurl + " page...\n"
    output += "<br>"
#figure out how to make this work more smarter
    if totalmatches % numrequests == (0 or 199):
        output += 'This wikipedia page has more edits in its history than can be handled by this app at this time. Shown below is information on the most recent ' + str(totalmatches) + ' edits.<br><br>'

    output += str(totalmatches) + " edits have been made to this page since "
    if totalmatches >= numrequests -1:
        output += datecreated.strftime('%Y/%m/%d') + ".<br>"
    else:
        output += "it was created on " + datecreated.strftime('%Y/%m/%d') + ".<br>"
    maxeditdaystr = maxeditday.strftime('%Y%m%d')
    output += 'The highest number of edits (' + str(matchdict[maxeditday]) + ') to the <a href="http://en.wikipedia.org/wiki/' + wikiurl + '">' + wikiurl + '</a> page occurred on <a href="http://en.wikipedia.org/w/index.php?title=' + wikiurl + '&offset=' + str(int(maxeditdaystr)+1) + '000000&limit=' + str(matchdict[maxeditday]) + '&action=history">' + maxeditday.strftime('%Y/%m/%d') + '</a>.<br><br>'

#convert matchdict to yeardict
    yeardict = {}
    for key in matchdict:
        if key.year not in yeardict:
            yeardict[key.year] = [0]*12
        yeardict[key.year][key.month-1] += matchdict[key]
        firstyear = min(yeardict)
        lastyear = max(yeardict)
        currentyear = firstyear + 1
        span = lastyear - firstyear + 1
#plug in blank rows for any years when there were no edits
        while currentyear < lastyear:
            if currentyear not in yeardict:
                yeardict[currentyear] = [0]*12
            currentyear += 1

#find maximum
    maxmonth = 0
    for key in yeardict:
        for item in yeardict[key]:
            if item > maxmonth:
                maxmonth = item

    color = maxmonth
    color = 255/float(color)
    monthtrunc = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Total"]
# turns yeardict into an html table with colors based on activity
#re-add "border=1" if you want the dividers
    htmltable = '<table style="width:100%; border-collapse:collapse; border-width:0px;"><tr><td></td>'
    for month in monthtrunc:
        htmltable += '<td>' + month + '</td>'
    htmltable += '</tr>'
    for key in yeardict:
        htmltable += '<tr><td>'+str(key)+'</td>'
        yeartotal = 0
        for i in range(0, 12):
            if i == 13:
                htmltable += '<td style="background-color:rgba(235,235,235,1);">%s</td>' % str(yeartotal)
            if yeardict[key][i] == 0:
                htmltable += '<td style="background-color:rgba(235,235,235,1);">%s</td>' % (str(yeardict[key][i]))
            else:
                red = yeardict[key][i]*color
                green = (maxmonth-yeardict[key][i])*color
                editspermonth = str(yeardict[key][i])
                yeartotal += yeardict[key][i]
                year = str(key)
                month = str(i+1)
                if len(month) == 1:
                    month = "0" + month
                htmltable += '<td id="cells" style="background-color:rgba(%i,%i,0,1);"><a href="http://en.wikipedia.org/w/index.php?title=%s&dir=prev&offset=%s%s00000000&limit=%s&action=history" target="_blank">%s</a></td>' % (red, green, wikiurl, year, month, editspermonth, editspermonth)
        htmltable += '<td style="text-align: center;">' + str(yeartotal) + '</td></tr>'
    htmltable += "</table>"

    output += htmltable
    totalSeconds = timeTotal.strftime('%S')
    output += '<br>These results took '+str(totalSeconds)+" seconds to execute."
    output = "<div class='responsestyle'>" + output + "</div>"
    return flask.Markup(output)

port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
