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


sets = [
    'COLOSSEUM',
    'EVOLUTION',
    'MYSTERY',
    'LABORATORY',
]

def randomize_cards(conf):
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
                y = conf['cards'][current_card]['group'] if conf['cards_by_evo'] else conf['cards'][current_card]['id']
                target.write('	db %s | NONE ; sets\n' % pick(sets, noise2d(10, y)))
            else:
                target.write(line)

cards = None
with open('cards.json') as file:
    cards = json.load(file)

randomize_cards({
    'cards': cards,
    'cards_by_evo': False,
})
