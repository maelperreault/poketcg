import json


# The base bit-noise constants were crafted to have distinctive and interesting
# bits, and have so far produced excellent experimental test results.
NOISE1 = 0xb5297a4d  # 0b0110'1000'1110'0011'0001'1101'1010'0100
NOISE2 = 0x68e31da4  # 0b1011'0101'0010'1001'0111'1010'0100'1101
NOISE3 = 0x1b56c4e9  # 0b0001'1011'0101'0110'1100'0100'1110'1001
PRIME1 = 0x0bd4bcb5  # 0b0000'1011'1101'0100'1011'1100'1011'0101
PRIME2 = 0x0063d68d  # 0b0000'0000'0110'0011'1101'0110'1000'1101

CAP = 1 << 32

def noise1d(n, seed=0):
    n *= NOISE1
    n += seed
    n ^= n >> 8
    n += NOISE2
    n ^= n << 8
    n *= NOISE3
    n ^= n >> 8
    return n % CAP

def noise2d(x, y, seed=0):
    return noise1d(x + PRIME1 * y, seed)

def noise3d(x, y, z, seed=0):
    return noise1d(x + PRIME1 * y + PRIME2 * z, seed)

def pick(l, n):
    return l[n % len(l)]

def calc_prize(p, r, n):
    offset = n % (r * 2) - r
    value = p + offset
    if value < 1:
        return 1
    elif value > 6:
        return 6
    return value

def calc_range(p, min, max):
    return p % (max - min + 1) + min

RAND_CARDS = 10
RAND_DECKS = 20
RAND_BOOSTERS = 30

def randomize_cards(conf, data):
    current_card = ''
    with open('templates/cards.asm', 'r') as src, open('src/data/cards.asm', 'w') as target:
        for i, line in enumerate(src):
            if 'CARD_NAME' in line:
                current_card = line.split(':')[0]
                target.write(line)
            elif 'RANDOMIZE_RARITY' in line:
                # @Todo add rarity randomizing?
                target.write(line)
            elif 'RANDOMIZE_SET' in line:
                y = data['cards'][current_card]['group'] if conf['cards_by_evo'] else data['cards'][current_card]['id']
                y *= 10
                target.write('	db %s | NONE ; sets\n' % pick(data['sets'], noise2d(RAND_CARDS, y, conf['seed'])))
            else:
                target.write(line)

def randomize_bank03(conf, data):
    with open('templates/bank03.asm', 'r') as src, open('src/engine/bank03.asm', 'w') as target:
        for i, line in enumerate(src):
            if '; DUEL:' in line:
                trainer = data['npc_duels'][line.split(':')[1].strip()]
                y = trainer['id'] * 10
                prize = trainer['prize']
                deck_id = trainer['deck_id']
                music_id = trainer['music_id']
                if not conf['exclude_prize']:
                    prize = calc_prize(prize, conf['prize_range'], noise3d(RAND_DECKS, y, 10, conf['seed']))
                if not conf['exclude_decks']:
                    deck_id = pick(data['decks'], noise3d(RAND_DECKS, y, 20, conf['seed']))
                if not conf['exclude_music']:
                    music_id = pick(data['music'], noise3d(RAND_DECKS, y, 30, conf['seed']))
                target.write('	start_duel PRIZES_{}, {}, {}\n'.format(prize, deck_id, music_id))
            elif '; BOOSTERS:' in line:
                trainer = data['npc_boosters'][line.split(':')[1].strip()]
                y = trainer['id'] * 10
                z = 10
                booster_count = 0
                boosters = []
                if conf['exclude_boosters']:
                    boosters = trainer['packs']
                else:
                    booster_count = calc_range(noise3d(RAND_BOOSTERS, y, z, conf['seed']), conf['booster_min'], conf['booster_max'])
                    for i in range(booster_count):
                        z += 10
                        boosters.append(pick(data['packs'], noise3d(RAND_BOOSTERS, y, z, conf['seed'])))

                remainder = booster_count % 3
                if remainder > 0:
                    boosters += ['NO_BOOSTER'] * (3 - remainder)
                booster_count = len(boosters)

                while len(boosters) >= 3:
                    booster_set = boosters[:3]
                    boosters = boosters[3:]
                    target.write('	give_booster_packs {}\n'.format(', '.join(booster_set)))
            else:
                target.write(line)

data = None
with open('data.json') as file:
    data = json.load(file)

seed = 1

randomize_cards({
    'seed': seed,
    'cards_by_evo': True
}, data)

randomize_bank03({
    'seed': seed,

    'prize_range': 1,
    'exclude_prize': False,
    'exclude_decks': False,
    'exclude_music': False,

    'booster_min': 2,
    'booster_max': 7,
    'exclude_boosters': False,
}, data)
