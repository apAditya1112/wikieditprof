import flask, flask.views
import os
import functools
import urllib2
import re
import operator
import webbrowser
from datetime import datetime
opener=urllib2.build_opener()
opener.addheaders=[('User-agent', 'Mozilla/5.0')]
app = flask.Flask(__name__)
app.secret_key = "bacon"

#users = {'miles':'bacon','chuck':'radio','sunah':'toast','cate':'hutch','sarah':'chair'}

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
# 
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
        result = prepare(input)
##        result = eval(flask.request.form['expression'])      
        flask.flash(result)
        return flask.redirect(flask.url_for('remote'))
    
app.add_url_rule('/',
                 view_func=Main.as_view('index'),
                 methods=["GET", "POST"])
app.add_url_rule('/remote/',
                 view_func=Remote.as_view('remote'),
                 methods=['GET', 'POST'])

def prepare(wikiurl):
	wikiurl=wikiurl.replace("%","%25")
	wikiurl=wikiurl.replace("'","%27")
	wikiurl=wikiurl.replace("&","%26")
	startTime=datetime.now()
	offset=""
	matchlist=""
	matchdict={}
	totalmatches=0
	output="Profiling the "+wikiurl+" page...\n"
	return scrapewiki(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output)

def scrapewiki(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output):
    matchesonpage=0
    url="http://en.wikipedia.org/w/index.php?title="+wikiurl+"&offset="+offset+"&limit=500&action=history"
    page=opener.open(url)
    while True:
        currentline=page.readline()
        if re.search(wikiurl+'\&amp;offset=(\d{14})',currentline):
            offset=re.search(wikiurl+'\&amp;offset=(\d{14})',currentline).group(1)
        if re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})',currentline):
            matchesonpage+=1
            edittimestamp=re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})',currentline)
            time = edittimestamp.group(1)
            day = edittimestamp.group(2)
            month = edittimestamp.group(3)
            monthlist=["January","February","March","April","May","June","July","August","September","October","November","December"]
            if month in monthlist:
                month = "%02d" % (monthlist.index(month)+1)
            year = edittimestamp.group(4)
            ddmmyyyy = str(day+"-"+month+"-"+year)
            if ddmmyyyy in matchdict:
                matchdict[ddmmyyyy]+=1
            else:
                matchdict[ddmmyyyy]=1
            matchlist += time + "\t" + day + "\t" + month + "\t" + year + "\n"
            totalmatches += 1
        if len(currentline)==0:
##            output += "matches found on first page: "+str(matchesonpage)+"\n"
            if matchesonpage>=499 and offset!="":
                return recursion(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output)
                break
            else:
                return dumpresults(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output)
                break

def recursion(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output):
    url="http://en.wikipedia.org/w/index.php?title="+wikiurl+"&offset="+offset+"&limit=500&action=history"
    page=opener.open(url)
    matchesonpage=0
    while True:
        currentline=page.readline()
        if re.search(wikiurl+'\&amp;offset=(\d{14})',currentline):
            if re.search(wikiurl+'\&amp;offset=(\d{14})',currentline).group(1)<offset:
                offset=re.search(wikiurl+'\&amp;offset=(\d{14})',currentline).group(1)
        if re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})',currentline):
            matchesonpage+=1
            edittimestamp=re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})',currentline)
            time = edittimestamp.group(1)
            day = edittimestamp.group(2)
            month = edittimestamp.group(3)
            monthlist=["January","February","March","April","May","June","July","August","September","October","November","December"]
            if month in monthlist:
                month = "%02d" % (monthlist.index(month)+1)
            year = edittimestamp.group(4)
            ddmmyyyy = str(day+"-"+month+"-"+year)
            if ddmmyyyy in matchdict:
                matchdict[ddmmyyyy]+=1
            else:
                matchdict[ddmmyyyy]=1
            matchlist += time + "\t" + day + "\t" + month + "\t" + year + "\n"
            totalmatches += 1
        if len(currentline)==0 and matchesonpage<499:
##            output += "matches on final page: "+str(matchesonpage)+"\n"
##            output += "A total of "+str(totalmatches)+" edits have been made to this page.\n"
            return dumpresults(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output)
            break
        if len(currentline)==0:
##            output += "matches found on this page: "+str(matchesonpage)+"\n"
##            output += "matches found so far: "+str(totalmatches)+"\n"
            if matchesonpage>=499:
##                output += "going to the next page\n"
                return recursion(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output)
                break
            
def dumpresults(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
##    print sortdict
    output+="A total of "+str(totalmatches)+" edits have been made to this page\n"
    maxeditday = max(matchdict.iteritems(), key=operator.itemgetter(1))[0]
    output += "The highest number of edits ("+ str(matchdict[maxeditday]) + ") to the "+wikiurl+" page occurred on " + str(maxeditday) + " (dd/mm/yyyy).\n"
    timeTotal=datetime.now()-startTime
    output += "This code took "+str(timeTotal)+" seconds to execute\n"
    return output
    
##    return
####not ideal:
##    sys.exit()
##    outfile=open(wikiurl+".html",'w')
##    outfile.write("testing")
##    outfile.close()
##    webbrowser.open(wikiurl+".html")
####only writes first 500 lines--variables not passing correctly
##    outcsv=open(wikiurl+".csv",'w')
##    outcsv.write(matchlist)
##    outcsv.close()

port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
