import requests
import re
from urllib.parse import urlparse, parse_qsl
import json
import sys
import getpass
import shutil
import os
import argparse

REDIRECT_URI = 'https://oauth.vk.com/blank.html'

class VKApi():
	def __init__(self, app_id=None, user_login=None, user_password=None, access_token=None, scope="photos", timeout=1):
		self.app_id = app_id
		self.user_login = user_login
		self.user_password = user_password

		self.uid = None

		self.scope = scope
		self.default_timeout = timeout

		if not access_token and (user_login or user_password):
			self.get_access_token()
		else:
			self.access_token = access_token

		self.session = requests.Session()

	def getUserLoginPassword(self):
		while True:
			if not self.user_login:
				print("Input your login")
				self.user_login = str(input())
				continue
			if not self.user_password:
				self.user_password = getpass.getpass()

	def get_access_token(self):
		if (not self.user_login) and (not self.user_password):
			self.getUserLoginPassword()

		session = requests.Session()

		# Login
		login_data = {
			'act': 'login',
			'utf8': '1',
			'email': self.user_login,
			'pass': self.user_password,
			'redirect_uri': REDIRECT_URI
		}

		response = session.post('https://login.vk.com', login_data)

		# OAuth2
		oauth_data = {
			'response_type': 'token',
			'client_id': '4655604',
			'scope': 'photos',
			'v': '5.33',
			'display': 'mobile',
		}
		response = session.post('https://oauth.vk.com/authorize', oauth_data)

		if 'access_token' not in response.url:
			form_action = re.findall(u'<form method="post" action="(.+?)">', response.text)
			if form_action:
				response = session.get(form_action[0])
			else:
				try:
					json_data = response.json()
				except ValueError:  # not json in response
					error_message = 'OAuth2 grant access error'
				else:
					error_message = 'VK error: [{0}] {1}'.format(
						json_data['error'],
						json_data['error_description']
					)
				session.close()
				print(error_message)
				sys.exit()

		session.close()

		parsed_url = urlparse(response.url)
		token_dict = dict(parse_qsl(parsed_url.fragment))
		if 'access_token' in token_dict:
			self.access_token = token_dict['access_token']
			self.expires_in = token_dict['expires_in']
		else:
			print('OAuth2 authorization error')
			print('May be wrong login/password combination')
			sys.exit()
		if 'user_id' in token_dict:
			self.uid = token_dict["user_id"]
		else:
			print("Cant get user id")
			sys.exit()

	def getTargetID(self):
		while True:
			print("Input id of the person, which album you want get (Also it may be yout own id)")
			targetID = str(input())
			for i in targetID:
				if i not in [str(x) for x in range(10)]:
					continue
			return targetID

	def downloadPhotos(self, photos, albumID):
		curDirectory = os.path.dirname(os.path.abspath(__file__))
		dirName = curDirectory + "\\" + albumID
		postfix = 1
		while True:
			if os.path.isdir(dirName):
				dirName += "({0})".format(postfix)
			else:
				break
		os.mkdir(dirName)
		urls = []
		for photo in photos:
			maxQ = 0
			cur = ""
			for key in photo:
				if key[0:5] == "photo":
					quality = int(key[6:])
					if quality > maxQ:
						cur = photo[key]
						maxQ = quality
			urls.append(cur)
		print("{count} photos to download".format(count=len(urls)))
		name = 1
		for url in urls:
			ext = "." + str(url.split(".")[-1])
			response = requests.get(url, stream=True)
			filename = dirName + "\\" + str(name) + ext
			with open(filename, "wb") as out:
				shutil.copyfileobj(response.raw, out)
			print("{name} downloaded...".format(name=name))
			name += 1
			del response
		print("check folder : {dir}".format(dir=dirName))

	def getPhotos(self):
		targetID = self.getTargetID()
		url = "https://api.vk.com/method/photos.getAlbums?owner_id={tid}&v=5.33".format(tid=targetID)
		result = json.loads(requests.get(url).text)
		albums=[]
		if 'response' in result:
			count =  result['response']['count']
			if count > 0:
				print("User with id={tid} has {count} albums:".format(tid=targetID, count=count))
			else:
				print("This user doesn't have albums")
			for i in range(result['response']['count']):
				cur = result['response']['items'][i]['id']
				albums.append(cur)
				print(cur)
		print("Which one you want to see?")
		while True:
			albumID = int(input())
			if albumID in albums:
				url = "https://api.vk.com/method/photos.get?owner_id={oid}&album_id={aid}&v=5.33&access_token={atoken}".format(
					oid=targetID, aid=albumID, atoken=self.access_token)
				result = json.loads(requests.get(url).text)
				result = result['response']
				count = result['count']
				photos = []
				for i in range(count):
					photos.append(result['items'][i])
				self.downloadPhotos(photos, str(albumID))
				return
			else:
				print("No such album, try again.")

def main(args):
	print("Input your login on vk.com")
	login = str(input())
	print("Input your password")
	password = getpass.getpass()
	api = VKApi(app_id="4655604", user_login=login, user_password=password)
	api.getPhotos()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="VK photos getter, no arguments")
	args = parser.parse_args()
	main(args)