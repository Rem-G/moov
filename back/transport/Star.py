import requests
from django.conf import settings
import shutil
from pathlib import Path
import datetime
from dateutil import tz
from .tools import *

#https://data.explore.star.fr/explore/?sort=title

class Star:
	def __init__(self):
		"""
			RENNES - STAR NETWORK
		"""
		self.network = "Star"
		self.city = "Rennes"
		self.next_departures_cache = {}
		self.station_lines_cache = {}

	def get_bus_stations(self):
		"""
			Get all bus stations of the network
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-topologie-pointsarret-td&q=&facet=nomstationparente&rows=10000"
		res = request(url)
		if len(res) > 0:
			return res.get("records")
		return []

	def get_metro_stations(self):
		"""
			Get all metro stations of the network
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-topologie-pointsarret-td&q=&facet=nomstationparente&rows=10000"
		res = request(url)
		if len(res) > 0:
			return res.get("records")
		return []

	def add_to_db(self, data, stations):
		"""
			Add stations to DB
			To prevent duplicates, the method return the list of inserted stations
		"""
		for station in data:
			name = station.get("fields").get("nom")
			if name not in stations:
				lon, lat = station.get("geometry").get("coordinates")
				add_station_db(station = name, network = self.city, lat = lat, lon = lon)
				stations.append(name)
		return stations


	def create_stations_db(self):
		"""
			Insert stations into database
			Download lines images
		"""
		stations = []
		stations = self.add_to_db(self.get_metro_stations(), stations)
		stations = self.add_to_db(self.get_bus_stations(), stations)
		self.download_img_all()
	
	def get_live_bus(self):
		"""
			Get live bus
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-vehicules-position-tr&q=&facet=numerobus&facet=nomcourtligne&facet=sens&facet=destination&rows=10000"
		return request(url).get("records")

	def get_bus_lines(self):
		"""
			Get bus lines
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-topologie-lignes-td&q=&facet=nomfamillecommerciale&rows=10000"
		return request(url).get("records")

	def download_img_all(self):
		"""
			Download lines logos
		"""
		for transport in self.get_bus_lines():
			self.download_img(transport)

		self.download_img({"fields": {"nomcourt": "a"}}, "metro")

	def download_img(self, transport, transport_type="bus"):
		if transport_type == "bus":
			url = f"https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-lignes-pictogrammes-dm&q=&facet=nomcourtligne&facet=date&facet=resolution&refine.nomcourtligne={transport.get('fields').get('nomcourt')}"
		else:
			url = f"https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-lignes-pictogrammes-dm&q=&facet=nomcourtligne&facet=date&facet=resolution&refine.nomcourtligne={transport.get('fields').get('nomcourt')}"
		img_id = ""
		for img in request(url).get("records"):
			if img.get('fields').get('image').get("width") == 100:
				img_id = img.get('fields').get('image').get('id')

		if len(img_id) > 0:
			if transport_type == "bus":
				line_img_url_dl = f"https://data.explore.star.fr/explore/dataset/tco-bus-lignes-pictogrammes-dm/files/{img_id}/download/"
			else:
				line_img_url_dl = f"https://data.explore.star.fr/explore/dataset/tco-metro-lignes-pictogrammes-dm/files/{img_id}/download/"

			r = requests.get(line_img_url_dl, stream = True)

			if r.status_code == 200:
				r.raw.decode_content = True
				path = Path(settings.STATICFILES_DIRS[0])
				with open(f"{path}/img/{transport.get('fields').get('nomcourt')}_{self.city}.png", "wb") as f:
					shutil.copyfileobj(r.raw, f)
				print('Image sucessfully Downloaded: ',img_id)
			else:
				print('Image Couldn\'t be retreived')
		
	def get_station_lines(self, station, transport_type="bus"):
 		url = f"https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-{transport_type}-topologie-dessertes-td&q=&facet=libellecourtparcours&facet=nomcourtligne&facet=nomarret&facet=estmonteeautorisee&facet=estdescenteautorisee&refine.nomarret={station}"
 		return set([line.get("fields").get("nomcourtligne") for line in request(url).get("records")])

	def get_station_lines_cache(self, station):
		if len(self.station_lines_cache) and station in self.station_lines_cache.keys():
			return self.station_lines_cache[station]
		else:
			station_lines = self.get_station_lines(station)
			self.station_lines_cache[station] = station_lines
			return station_lines

	def get_topo(self, station):
		"""
			Return the topography of lines linked to the station
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-topologie-parcours-td&q=&facet=idligne&facet=nomcourtligne&facet=senscommercial&facet=type&facet=nomarretdepart&facet=nomarretarrivee&facet=estaccessiblepmr&rows=10000"
		res = []

		if len(self.next_departures_cache) and station in self.next_departures_cache.keys():
			current_lines = set([rec.get("line") for rec in self.next_departures_cache[station]])
		else:
			current_lines = set([rec.get("line") for rec in self.get_station_next_depart(station)])
		
		for record in request(url).get("records"):
			if record.get("fields").get("nomcourtligne") in current_lines:
				res.append(record)

		metro_url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-topologie-parcours-td&q=&facet=idligne&facet=nomcourtligne&facet=senscommercial&facet=type&facet=nomarretdepart&facet=nomarretarrivee&facet=estaccessiblepmr&rows=10000&refine.nomcourtligne=a"
		res += request(metro_url).get("records")

		return self.convert_coor_topo(res)

	def convert_coor_topo(self, records):
		"""
			Invert coordinates to match Leaflet requirements
		"""
		for index, record in enumerate(records):
			for coor_index, coor in enumerate(record.get("fields").get("parcours").get("coordinates")):
				records[index]["fields"]["parcours"]["coordinates"][coor_index] = [coor[1], coor[0]]

		return records

	def convert_coor_live(self, records):
		"""
			Invert coordinates to match Leaflet requirements
		"""
		for index, record in enumerate(records):
			coor = record["geometry"]["coordinates"]
			records[index]["geometry"]["coordinates"] = [coor[1], coor[0]]

		return records

	def get_live_bus_station(self, station):
		"""
			Get live bus for a given station
			The method gathers all the lines associated to the given station and fetch the live buses accordingly
		"""
		res = []

		for record in self.get_live_bus():
			if record.get("fields").get("nomcourtligne") in self.get_station_lines_cache(station):
				res.append(record)		
		return self.convert_coor_live(res)

	
	def check_dt(self, dt):
		"""
			Check if datetime > now
		"""
		dt_obj = datetime.datetime.strptime(dt.split('+')[0], '%Y-%m-%dT%H:%M:%S')
		current_tz = tz.gettz("Europe/Paris")
		utc_now = datetime.datetime.now()
		now = utc_now.astimezone(current_tz).replace(tzinfo=None)

		if dt_obj > now:
			return True
		return False

	def add_0_to_dt(self, dt):
		"""
			Add 0 to string datetime
			Ex : 1:10 -> 01:10
		"""
		for key, value in dt.items():
			if len(str(value)) == 1:
				dt[key] = "0"+str(value)
		return dt

	def convert_dt_string(self, dt):
		"""
			Convert datetime in string format hh:mm
		"""
		dt_obj = datetime.datetime.strptime(dt.split('+')[0], '%Y-%m-%dT%H:%M:%S')
		dt_obj_str = self.add_0_to_dt({"hour": dt_obj.hour, "min": dt_obj.minute})

		return f"{dt_obj_str['hour']}:{dt_obj_str['min']}"

	def format_next_departures(self, records):
		"""
			Format recorded next departures
		"""
		data = []

		for line, line_value in records.items():
			for dest, dest_value in line_value.items():
				data.append({"line": line, "destination": dest, "next_departures": dest_value.get("next_departures")})

		return data

	def get_station_lines_names(self, station):
		"""
			Get lines names for a given station
		"""
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-topologie-dessertes-td&q=&sort=idparcours&facet=libellecourtparcours&facet=nomcourtligne&facet=nomarret&facet=estmonteeautorisee&facet=estdescenteautorisee&refine.nomarret={}".format(station)
		station_lines = request(url).get("records")

		#metro
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-circulation-passages-tr&q=&facet=nomcourtligne&facet=sens&facet=destination&facet=nomarret&facet=precision&timezone=Europe/Paris&refine.nomarret={}".format(station)
		station_lines += request(url).get("records")
		
		return set([line.get("fields").get("nomcourtligne") for line in station_lines])

	def get_station_next_depart(self, station):
		"""
			Get all next departures for a given station
		"""
		data = {}
		#bus
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-topologie-dessertes-td&q=&sort=idparcours&facet=libellecourtparcours&facet=nomcourtligne&facet=nomarret&facet=estmonteeautorisee&facet=estdescenteautorisee&refine.nomarret={}".format(station)
		station_lines = request(url).get("records")

		#metro
		url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-circulation-passages-tr&q=&facet=nomcourtligne&facet=sens&facet=destination&facet=nomarret&facet=precision&timezone=Europe/Paris&refine.nomarret={}".format(station)
		station_lines += request(url).get("records")
		
		id_lines = set([line.get("fields").get("idligne") for line in station_lines])

		for id_line in id_lines:
			if id_line == "1001":#metro
				url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-metro-circulation-passages-tr&q=&sort=-depart&facet=nomcourtligne&facet=sens&facet=destination&facet=nomarret&facet=precision&facet=idligne&refine.idligne={}&refine.nomarret={}&rows=60&timezone=Europe/Paris".format(id_line, station)
			else:
				url = "https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-bus-circulation-passages-tr&q=&sort=-depart&facet=idligne&facet=nomcourtligne&facet=sens&facet=destination&facet=precision&facet=nomarret&refine.idligne={}&refine.nomarret={}&rows=40&timezone=Europe/Paris".format(id_line, station)
			
			line_infos = request(url).get("records")

			for rec in line_infos:
				line = rec.get("fields").get("nomcourtligne")
				dest = rec.get("fields").get("destination")

				if not line in data.keys():
					data[line] = {}

				if not dest in data[line].keys():
					data[line][dest] = {}
					data[line][dest]["next_departures"] = []
				
				depart_var = "departtheorique"
				if line == 'a':
					depart_var = "depart"

				if self.check_dt(rec.get("fields").get(depart_var)) and len(data[line][dest]["next_departures"]) < 3:
					data[line][dest]["next_departures"].append(self.convert_dt_string(rec.get("fields").get(depart_var)))
		res = self.format_next_departures(data)
		self.next_departures_cache = {station: res}
		return res


	def get_alertes_trafic(self):
		"""
			Get all trafic alerts for a given network
		"""
		alertes = request('https://data.explore.star.fr/api/records/1.0/search/?dataset=tco-busmetro-trafic-alertes-tr&q=&rows=10000&facet=niveau&facet=debutvalidite&facet=finvalidite&facet=idligne&facet=nomcourtligne&timezone=Europe/Paris').get('records')
		res = {}
		res['BUS'] = []
		res['METRO'] = []
		res['TRAM'] = []

		for alerte in alertes:
			if alerte['fields']['niveau'] == "Majeure":
				dt = datetime.datetime.strptime(alerte["fields"]['debutvalidite'].split("+")[0], "%Y-%m-%dT%H:%M:%S")
				dt_dict = self.add_0_to_dt({"hour": dt.hour, "min": dt.minute})

				a = {}
				a['ligne_cli'] = alerte["fields"]['nomcourtligne']
				a['debut'] = f"{dt.day}-{dt.month}-{dt.year} {dt_dict['hour']}:{dt_dict['min']}"
				a['titre'] = alerte["fields"]['titre']
				a['message'] = alerte["fields"]['description']
				if alerte["fields"]['nomcourtligne'] == "A":
					res['METRO'].append(a)
				else:
					res['BUS'].append(a)

		return res 

	def get_line_frequentation(self, line):
		"""
			Get frequentation for a given line
		"""
		if line == "a":
			line = "Ligne a"

		weekday = datetime.datetime.today().weekday()

		day_string = "Lundi-vendredi"
		if weekday == 5:
			day_string = "Samedi"
		elif weekday == 6:
			day_string = "Dimanche"
		day_string = "Lundi-vendredi"

		url = f"https://data.explore.star.fr/api/records/1.0/search/?dataset=mkt-frequentation-niveau-freq-max-ligne&q=&sort=tranche_horaire&facet=materiel&facet=jour_semaine&facet=ligne&facet=tranche_horaire&facet=frequentation&facet=niveau_frequentation&refine.ligne={line}&refine.jour_semaine={day_string}&rows=100"
		res = request(url).get("records")

		return self.format_line_frequentation(res)

	def format_line_frequentation(self, records):
		"""
			Format the line frequentations data to display it in a chart
		"""
		labels = []
		values = []

		for rec in records:
			if rec.get("fields").get("niveau_frequentation"):
				labels.append(rec.get("fields").get("tranche_horaire"))
				values.append(rec.get("fields").get("niveau_frequentation"))

		current_tz = tz.gettz("Europe/Paris")
		utc_now = datetime.datetime.now()
		now = utc_now.astimezone(current_tz).replace(tzinfo=None)

		current_index = len(labels)-1

		for label_index, label in enumerate(labels):
			label_dt = datetime.datetime.strptime(f'{now.day}-{now.month}-{now.year} {label}', '%d-%m-%Y %H:%M')

			if label_index < len(labels)-1:
				next_label_dt = datetime.datetime.strptime(f"{now.day}-{now.month}-{now.year} {labels[label_index+1]}", '%d-%m-%Y %H:%M')
				if now >= label_dt and now < next_label_dt:
					current_index = label_index

			if label_index % 5 != 0 and label_index > 0:
				labels[label_index] = ""
			
		labels[current_index] = "Now"

		return ({"labels": labels, "values": values, "current_index": current_index,})