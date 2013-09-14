#!/usr/bin/python

from BeautifulSoup import BeautifulSoup as Soup
from soupselect import select
import urllib
import re
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os.path
import sys
import time
from time import strftime
from xml.dom.minidom import parse, parseString

import config

separator = '\n\n'
defaultEncoding = 'utf-8'
emptyfeed = '<rss version="2.0"><channel><title>MailWebsiteChanges Feed</title><link>https://github.com/Debianguru/MailWebsiteChanges</link><description>The MailWebsiteChanges Feed</description></channel></rss>'


def parseSite(uri, css, regex):
        content, warning = None, None

        try:
                file = urllib.urlopen(uri)
        except IOError as e:
                warning = 'WARNING: could not open URL; maybe content was moved?\n\n' + str(e)
                return content, warning

        if css == '':
                content = file.read()
        else:
                soup = Soup(file)

                result = select(soup, css)
                if len(result) == 0:
                        warning = "WARNING: selector became invalid!"
                else:
                        content = separator.join(map(str, result))

        if regex != '':
                result = re.findall(r'' + regex, content)
                if result == None:
                        warning = "WARNING: regex became invalid!"
                else:
                        content = separator.join(result)

        file.close()
        return content, warning


def sendmail(subject, content, sendAsHtml, encoding, link):
        if sendAsHtml:
                if link != None:
                        content = '<p><a href="' + link + '">' + subject + '</a></p>\n' + content
                mail = MIMEText('<html><head><title>' + subject + '</title></head><body>' + content + '</body></html>', 'html', encoding)
        else:
                if link != None:
                        content = link + '\n\n' + content
                mail = MIMEText(content, 'text', encoding)

        mail['From'] = config.sender
        mail['To'] = config.receiver
        mail['Subject'] = Header(subject, encoding)

        s = smtplib.SMTP(config.smtptlshost, config.smtptlsport)
        s.ehlo()
        s.starttls()
        s.login(config.smtptlsusername, config.smtptlspwd)
        s.sendmail(config.sender, config.receiver, mail.as_string())
        s.quit()


def pollWebsites():

        if config.rssfile != '':
                if os.path.isfile(config.rssfile):
                        feedXML = parse(config.rssfile)
                else:
                        feedXML = parseString(emptyfeed)


        for site in config.sites:

                fileContent = None

                if os.path.isfile(site[0] + '.txt'):
                        file = open(site[0] + '.txt', 'r')
                        fileContent = file.read()
                        file.close()

		print 'polling site [' + site[0] + '] ...'
                content, warning = parseSite(site[1], site[2], site[3])

                if warning:
                        subject = '[' + site[0] + '] WARNING'
                        print 'WARNING: ' + warning
                        if config.receiver != '':
                                sendmail(subject, warning, False, defaultEncoding, None)
                elif content != fileContent:
                        print '[' + site[0] + '] has been updated.'

                        file = open(site[0] + '.txt', 'w')
                        file.write(content)
                        file.close()

                        if fileContent:
                                subject = '[' + site[0] + '] ' + config.subjectPostfix
                                if config.receiver != '':
                                        sendmail(subject, content, (site[2] != ''), site[4], site[1])

                                if config.rssfile != '':
                                        feeditem = feedXML.createElement('item')
                                        titleitem = feedXML.createElement('title')
                                        titleitem.appendChild(feedXML.createTextNode(subject))
                                        feeditem.appendChild(titleitem)
                                        linkitem = feedXML.createElement('link')
                                        linkitem.appendChild(feedXML.createTextNode(site[1]))
                                        feeditem.appendChild(linkitem)
                                        descriptionitem = feedXML.createElement('description')
                                        descriptionitem.appendChild(feedXML.createTextNode(subject))
                                        feeditem.appendChild(descriptionitem)
                                        dateitem = feedXML.createElement('pubDate')
                                        dateitem.appendChild(feedXML.createTextNode(strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime())))
                                        feeditem.appendChild(dateitem)

                                        feedXML.getElementsByTagName('channel')[0].appendChild(feeditem)

        if config.rssfile != '':
                file = open(config.rssfile, 'w')
                file.write(feedXML.toxml())
                file.close()


if __name__ == "__main__":
        try:
                pollWebsites()
        except:
                msg = separator.join(map(str,sys.exc_info()))
                print msg
                if config.receiver != '':
                        sendmail('[MailWebsiteChanges] Something went wrong ...', msg, False, defaultEncoding, None)

