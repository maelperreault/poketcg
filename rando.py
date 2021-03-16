from random import choice

old_lines = None
with open('src/data/cards.asm', 'r') as file:
    old_lines = file.readlines()
new_lines = []

types = [
    'TYPE_PKMN_FIRE',
    'TYPE_PKMN_GRASS',
    'TYPE_PKMN_LIGHTNING',
    'TYPE_PKMN_WATER',
    'TYPE_PKMN_FIGHTING',
    'TYPE_PKMN_PSYCHIC',
    'TYPE_PKMN_COLORLESS',
]

sets = [
    'COLOSSEUM',
    'EVOLUTION',
    'MYSTERY',
    'LABORATORY',
]

for l in old_lines:
    if ' ; type' in l and 'ENERGY' not in l and 'TRAINER' not in l:
        l = '	db %s ; type\n' % choice(types)
    elif ' ; set' in l and 'ENERGY' not in l:
        l = '	db %s | NONE ; sets\n' % choice(sets)
    new_lines.append(l)

with open('src/data/cards.asm', 'w') as file:
    file.writelines(new_lines)
