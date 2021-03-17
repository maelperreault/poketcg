import json
import jsonpickle
from enum import Enum

BASIC = 0
STAGE1 = 1
STAGE2 = 2
NONE = 3

def get_stage(key):
    if key == 'BASIC':
        return BASIC
    elif key == 'STAGE1':
        return STAGE1
    elif key == 'STAGE2':
        return STAGE2
    elif key == 'NONE':
        return NONE
    return NONE

class Card(object):
    def __init__(self, name, group):
        self.name = name
        self.text_name = ''
        self.id = group
        self.group = group
        self.uses_attacks = False
        self.stage = NONE
        self.current_attack = 0
        self.energy = {}
        self.target_group = ''

    def __str__(self):
        return 'Card(Name: {name}, ID: {id}, Group: {group}, Stage: {stage})'.format(**self.__dict__)

    def is_evolution(self):
        return self.stage == STAGE1 or self.stage == STAGE2


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
    
        elif ' ; name' in line:
            current_card.text_name = line.split(' ')[1]
            card_names[current_card.text_name] = current_card

        elif ' ; stage' in line:
            current_card.stage = get_stage(line.split(' ')[1])

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
            card.group = card_names[card.target_group].group

with open('cards.json', 'w') as file:
    file.write(jsonpickle.encode(cards, unpicklable=False, indent=2))
