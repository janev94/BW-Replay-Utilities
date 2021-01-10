import os
import binascii
import zlib
import struct
import datetime
import functools
import argparse

FRAME_TO_MILLIS = 42

def is_zlib_compressed(data):
    unsigned_byte = data[1] & 0xFF
    return data[0] == 0x78 and (unsigned_byte in [0x9c, 0x01, 0x5e, 0xda])


def read_int(*, buffer, start_idx):
    return int.from_bytes(buffer[start_idx:start_idx+4], byteorder='little')


def check_replay_version(content):
    # Modern Replays 1.21+ start have 12-15 bytes == seRS
    if bytes.decode(content[12:12+4]) != 'seRS':
        raise Exception("Replay File is of unsupported version")


def parse_replay_header(content):
    headers = {}
    # for our sake we can ignore the first 16 bytes, as these identify the replay file and we only support 1.21 for now
    hdr_len_bytes = content[28:32]
    _hdr_len_int = int.from_bytes(hdr_len_bytes, byteorder='little')
    compressed_hdr = is_zlib_compressed(content[32:])

    if compressed_hdr:
        decompressed = zlib.decompress(content[32:32+633])
    else:
        decompressed = content[32:]

    frame_count = read_int(buffer=decompressed, start_idx=1)
    secs = frame_count * 42 / 1000
    headers['time_seconds'] = secs
    duration = datetime.timedelta(seconds=secs)
    duration = str(duration).split('.')[0] # remove millisecond part, we do not want to be _that_ precise
    headers['time_formatted'] = duration

    start_time = read_int(buffer=decompressed, start_idx=8)
    dt = datetime.datetime.fromtimestamp(start_time)
    headers['start_time'] = str(dt)
    headers['start_time_ts'] = start_time

    map_name = decompressed[97: 97 + 26]
    map_name = map_name.strip()
    map_name = map_name.strip(b'\x00')
    map_name = map_name.decode()

    headers['map_name'] = map_name

    headers['player_info'] = get_player_data(decompressed[161: 161 + 432])

    return headers


def get_player_data(player_buffer):
    player_data = []

    SLOTS_COUNT = 12 # 8 players + 4 observers
    # MAX_PLAYERS = 8
    PLAYER_CHUNK_SIZE = len(player_buffer) // SLOTS_COUNT

    for i in range(SLOTS_COUNT):
        player_chunk_bytes = player_buffer[i*PLAYER_CHUNK_SIZE: i*PLAYER_CHUNK_SIZE + PLAYER_CHUNK_SIZE] # get the next PLAYER_CHUNK_SIZE bytes to decode player info
        
        player = {}
        player['slot_id'] = int.from_bytes(player_chunk_bytes[0:2], byteorder='little')
        player['player_id'] = player_chunk_bytes[4]
        player['player_type'] = player_chunk_bytes[8]
        player['player_race'] = player_chunk_bytes[9]
        player['player_team'] = player_chunk_bytes[10]
        player['player_name'] = player_chunk_bytes[11: 11+25]

        # # Colour info
        # slot_colour_start_idx = 593 + i * 4
        # player['colour'] = read_int(buffer = player_buffer, start_idx=slot_colour_start_idx)


        r = functools.reduce(lambda a,b: a+b, player['player_name'])
        if r:
            player['player_name'] = player['player_name'].decode().strip('\x00')
            player_data.append(player)

    return player_data


def parse(fname):
    with open(fname, 'rb') as f:
        content = f.read()
    
    check_replay_version(content)

    headers = parse_replay_header(content)

    return headers


def batch_parse(parser):
    args = parser.parse_args()
    replay_root = args.rep_root

    for path, _, files in os.walk(replay_root):
        if files:
            # series_length = 0
            # players_series = set()
            for rep in files:
                if not rep.endswith('.rep'):
                    continue
                fname = os.path.join(path, rep)
                headers = parse(fname)
                players_list = set([ x['player_name'] for x in headers['player_info'] ])

                print(f'{fname}: {headers["time_formatted"]} {players_list}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SC:R replay statistics")

    parser.add_argument('--rep_root', default='.')
    parser.add_argument('--screp_bin', default='.')
    batch_parse(parser)
