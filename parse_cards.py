import json
import jsonpickle
from enum import Enum

TYPE_PKMN = 0
TYPE_ENERGY = 1
TYPE_TRAINER = 2

STAGE_BASIC = 0
STAGE_1 = 1
STAGE_2 = 2
STAGE_NONE = 3

def get_type(key):
    if 'TYPE_PKMN' in key:
        return TYPE_PKMN
    if 'TYPE_ENERGY' in key:
        return TYPE_ENERGY
    if 'TYPE_TRAINER' in key:
        return TYPE_TRAINER
    return TYPE_PKMN

def get_stage(key):
    if key == 'BASIC':
        return STAGE_BASIC
    elif key == 'STAGE1':
        return STAGE_1
    elif key == 'STAGE2':
        return STAGE_2
    return STAGE_NONE

class Card(object):
    def __init__(self, name, group):
        self.name = name
        self.text_name = ''
        self.id = group
        self.group = group
        self.constant = ''
        self.type = TYPE_PKMN
        self.stage = STAGE_NONE
        self.limit = 2
        self.has_evolution = False
        self.uses_attacks = False
        self.energy = {}
        self.target_group = ''

    def __str__(self):
        return 'Card(Name: {name}, ID: {id}, Group: {group}, Stage: {stage})'.format(**self.__dict__)

    def is_evolution(self):
        return self.stage == STAGE_1 or self.stage == STAGE_2


cards = {}
card_names = {}
card_group_id = 0

current_card = None

with open('src/data/cards.asm', 'r') as file:
    for i, line in enumerate(file):
        if 'Card: ; ' in line: # is the start of a new card
            card_group_id += 1
            current_card = Card(line.split(':')[0], card_group_id)
            cards[current_card.name] = current_card

        elif ' ; type' in line:
            current_card.type = get_type(line.split(' ')[1])

        elif ' ; name' in line:
            current_card.text_name = line.split(' ')[1]
            card_names[current_card.text_name] = current_card

        elif ' ; stage' in line:
            current_card.stage = get_stage(line.split(' ')[1])

        elif ' ; const' in line:
            current_card.constant = line.split(' ')[1]

        elif (
            current_card \
            and current_card.is_evolution() \
            and ' ; pre-evo name' in line
        ):
            current_card.target_group = line.split(' ')[1]

        elif ' ; energies' in line:
            energies = line[8:-11].split(',')
            if len(energies) < 2:
                pass
            else:
                for i in range(0, len(energies), 2):
                    color = energies[i].strip()
                    count = int(energies[i+1])
                    current_card.energy[color] = current_card.energy.get(color, 0) + count
                current_card.uses_attacks = True

for i in range(3):
    for card in cards.values():
        if card.is_evolution():
            preevo = card_names[card.target_group]
            preevo.has_evolution = True
            card.group = preevo.group
            card.has_evolution = True

            if preevo.stage == STAGE_BASIC:
                preevo.limit = 4
            elif preevo.stage == STAGE_1:
                preevo.limit = 2
            if card.stage == STAGE_2:
                card.limit = 1
        elif card.type == TYPE_ENERGY:
            card.limit = 60

with open('cards.json', 'w') as file:
    file.write(jsonpickle.encode(cards, unpicklable=False, indent=2))

with open('cards.json', 'r') as file:
    cards = json.load(file)

def uses_energy(energy):
    return lambda x: (x['type'], x['has_evolution']) == (0, False) and energy in x['energy']

def is_pokemon_card():
    return lambda x: x['type'] == TYPE_TRAINER

def is_energy_card():
    return lambda x: x['type'] == TYPE_ENERGY

def is_trainer_card():
    return lambda x: x['type'] == TYPE_TRAINER

def pkmn_by_evolution(cards, has_evolution=False):
    return filter(lambda x: x['has_evolution'] == has_evolution, cards)

def pkmn_by_stage(cards, stage=STAGE_BASIC):
    return filter(lambda x: x['stage'] == stage, cards)

def pkmn_by_energy(cards, energy):
    return filter(lambda x: energy in x['energy'], cardS)

def pkmn_colorless(cards):
    return filter(lambda x: ('COLORLESS' in x['energy'], len(x['energy'])) == (True, 1), cards)


thing = pkmn_colorless(pkmn_by_stage(pkmn_by_evolution(cards.values(), True), 1))
print(list(thing))
