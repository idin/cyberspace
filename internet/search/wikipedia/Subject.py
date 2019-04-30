from chronology import get_elapsed, get_now


class Entity:
	pass


class Person(Entity):
	def __init__(self, firstname, lastname, birthdate, deathdate=None, birthplace=None, occupation=None):
		self.firstname = firstname
		self.lastname = lastname
		self.birthdate = birthdate
		self.deathdate = deathdate
		self.birthplace = birthplace
		self.occupation = occupation

	@property
	def age(self):
		if self.deathdate:
			return get_elapsed(start=self.birthdate, end=self.deathdate, unit='year')
		else:
			return get_elapsed(start=self.birthdate, unit='year')


class Location(Entity):
	pass


class Organization(Entity):
	pass


class WorkOfArt(Entity):
	pass


class ConsumerGood(Entity):
	pass


class Corporation(Organization):
	pass
