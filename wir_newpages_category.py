	#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Based on wir_newpages.py
# Created 13 Jul 2019

# Import modules
import pywikibot
from wir_newpages import *
import requests


wdsite = pywikibot.Site('wikidata', 'wikidata')
repo = wdsite.data_repository()
langs = ['en','de', 'es', 'simple', 'fr']
for lang in langs:
	wikisite = pywikibot.Site(lang, 'wikipedia')
	if lang == 'en':
		targetcats = ['Category:Date of birth not in Wikidata', 'Category:Date of death not in Wikidata','Category:Articles without Wikidata item']
	elif lang == 'de':
		targetcats = ['Kategorie:Wikipedia:Artikel ohne Wikidata-Datenobjekt']
	elif lang = 'simple':
		targetcats = ['Category:Articles without Wikidata item']
	elif lang = 'fr':
		targetcats = ['Catégorie:Wikipédia:Article sans élément Wikidata associé']
	for targetcat in targetcats:
		cat = pywikibot.Category(wikisite, targetcat)
		pages = pagegenerators.CategorizedPageGenerator(cat, recurse=False)
		for page in pages:
			print(page.title())
			if page.isRedirectPage():
				continue
			if not pageIsBiography(page=page, lang=lang):
				continue
			print('\n==', page.title().encode('utf-8'), '==')
			gender = calculateGender(page=page, lang=lang)
			item = ''
			try:
				item = pywikibot.ItemPage.fromPage(page)
			except:
				null = 0

			if item:
				print('Page has item')
				print('https://www.wikidata.org/wiki/%s' % (item.title()))
				item.get()
				skip = True
				if item.claims:
					if 'P31' in item.claims:
						for p31 in item.claims['P31']:
							if p31.getTarget().title() != 'Q5':
								skip = True
								continue
					else:
						continue
				else:
					continue
				if skip:
					continue
				# test = input('Continue?')
				addBiographyClaims(repo=repo, wikisite=wikisite, item=item, page=page, lang=lang)
				page.touch()
			else:
				print('Page without item')
				#search for a valid item, otherwise create
				if authorIsNewbie(page=page, lang=lang):
					print("Newbie author, checking quality...")
					if pageIsRubbish(page=page, lang=lang) or \
					   (not pageCategories(page=page, lang=lang)) or \
					   (not pageReferences(page=page, lang=lang)) or \
					   (not len(list(page.getReferences(namespaces=[0])))):
						print("Page didnt pass minimum quality, skiping")
						continue

				print(page.title().encode('utf-8'), 'need item', gender)
				wtitle = page.title()
				wtitle_ = wtitle.split('(')[0].strip()
				searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&format=xml' % (urllib.parse.quote(wtitle_), lang)
				raw = getURL(searchitemurl)
				print(searchitemurl.encode('utf-8'))

				#check birthdate and if it matches, then add data
				numcandidates = '' #do not set to zero
				if not '<search />' in raw:
					m = re.findall(r'id="(Q\d+)"', raw)
					numcandidates = len(m)
					print("Found %s candidates" % (numcandidates))
					if numcandidates > 5: #too many candidates, skiping
						print("Too many, skiping")
						continue
					for itemfoundq in m:
						itemfound = pywikibot.ItemPage(repo, itemfoundq)
						itemfound.get()
						if ('%swiki' % (lang)) in itemfound.sitelinks:
							print("Candidate %s has sitelink, skiping" % (itemfoundq))
							numcandidates -= 1
							continue
						pagebirthyear = calculateBirthYear(page=page, lang=lang)
						pagebirthyear = pagebirthyear and int(pagebirthyear.split('-')[0]) or ''
						if not pagebirthyear:
							print("Page doesnt have birthdate, skiping")
							break #break, dont continue. Without birthdate we cant decide correctly
						if 'P569' in itemfound.claims:
							try:
								print(itemfound.claims['P569'][0].getTarget().precision in [9, 10, 11])
							except:
								continue
							if itemfound.claims['P569'][0].getTarget().precision in [9, 10, 11]:
								#https://www.wikidata.org/wiki/Help:Dates#Precision
								itemfoundbirthyear = int(itemfound.claims['P569'][0].getTarget().year)
								print("candidate birthdate = %s, page birthdate = %s" % (itemfoundbirthyear, pagebirthyear))
								mindatelen = 4
								if len(str(itemfoundbirthyear)) != mindatelen or len(str(pagebirthyear)) != mindatelen:
									print("%s birthdate length != %s" % (itemfoundq, mindatelen))
									continue
								#reduce candidates if birthyear are different
								minyeardiff = 3
								if itemfoundbirthyear >= pagebirthyear + minyeardiff or itemfoundbirthyear <= pagebirthyear - minyeardiff:
									print("Candidate %s birthdate out of range, skiping" % (itemfoundq))
									numcandidates -= 1
									continue
								#but only assume it is the same person if birthyears match
								if itemfoundbirthyear == pagebirthyear:
									print('%s birthyear found in candidate %s. Category:%s births found in page. OK!' % (itemfoundbirthyear, itemfoundq, itemfoundbirthyear))
									# test = input('Continue?')
									print('Adding sitelink %s:%s' % (lang, page.title().encode('utf-8')))
									try:
										itemfound.setSitelink(page, summary='Adding sitelink: [[:%s:%s|%s]] (%s)' % (lang, page.title(), page.title(), lang))
									except:
										print("Error adding sitelink. Skiping.")
										break
									# test = input('Continue?')
									addBiographyClaims(repo=repo, wikisite=wikisite, item=itemfound, page=page, lang=lang)
									# Touch the page to force an update
									try:
										page.touch()
									except:
										null = 0
									break

				# no item found, or no candidates are useful
				if '<search />' in raw or (numcandidates == 0):
					print('No useful item found. Creating a new one...')
					# test = input('Continue?')
					#create item
					newitemlabels = {'en': wtitle_,'de': wtitle_,'fr': wtitle_,'es': wtitle_,'pt': wtitle_}
					newitem = pywikibot.ItemPage(repo)
					newitem.editLabels(labels=newitemlabels, summary="Creating item for [[:%s:%s|%s]] (%s): %s %s" % (lang, wtitle, wtitle, lang, 'human', gender))
					newitem.get()
					try:
						newitem.setSitelink(page, summary='Adding sitelink: [[:%s:%s|%s]] (%s)' % (lang, page.title(), page.title(), lang))
					except:
						print("Error adding sitelink. Skiping.")
						break
					addBiographyClaims(repo=repo, wikisite=wikisite, item=newitem, page=page, lang=lang)
					# Touch the page to force an update
					try:
						page.touch()
					except:
						null = 0
					# exit()
