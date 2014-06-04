#!/usr/bin/python
# coding:utf-8

"""

1. mysqlのインストール
  $ sudo apt-get install mysql-server libmysqlclient-dev

2. python-mysqlのインストール
  $ sudo pip install python-mysql

3. peeweeのインストール
  $ sudo pip install peewee

"""

from peewee import *
from datetime import date

import sys

# MySQL
#db = MySQLDatabase('testdb', host='localhost', user='testuser', passwd='1q2w3e4r')

# SQlite
db = SqliteDatabase('people.db')

# person table class
class Person(Model):
    name = CharField()
    birthday = DateField()
    is_relative = BooleanField()

    class Meta:
        database = db  # this model uses the people database


# pet table class
class Pet(Model):
    owner = ForeignKeyField(Person, related_name='pets')
    name = CharField()
    animal_type = CharField()

    class Meta:
        database = db  # this model uses the people database


if '__main__' == __name__:
    # connect
    try:
        db.connect()
    except:
        # error
        sys.exit("Failed to connect database.")

    # create table 
    try:
        Person.create_table()
        Pet.create_table()
    except:
        Pet.delete().execute()
        Person.delete().execute()
        
    # more clever approach
    """
    with db.transaction():
        for i in range(0,1000):
            item1 = Person.create(name=i, birthday=date(1972,8,2), is_relative=True)
            item2 = Pet.create(owner=item1, name='Kitty', animal_type='cat')
    """


    # naive approach
    for i in range(0,1000):
        item1 = Person.create(name=i, birthday=date(1972,8,2), is_relative=True)
        item2 = Pet.create(owner=item1, name='Kitty', animal_type='cat')

"""
    # Storing data
    uncle_bob = Person(name='Bob', birthday=date(1972,8,2), is_relative=True)
    uncle_bob.save()

    # automatic add (Model.create())
    grandma = Person.create(name='Grandma', birthday=date(1900,12,25), is_relative=True)
    herb = Person.create(name='Herb', birthday=date(1950, 5, 5), is_relative=False)

    grandma.name = 'Grandma L.'
    grandma.save()

    # add pet
    bob_kitty = Pet.create(owner=uncle_bob, name='Kitty', animal_type='cat')
    herb_fido = Pet.create(owner=herb, name='Fido', animal_type='dog')
    herb_mittens = Pet.create(owner=herb, name='Mittens', animal_type='cat')
    herb_mittens_jr = Pet.create(owner=herb, name='Mittens Jr', animal_type='cat')
"""
