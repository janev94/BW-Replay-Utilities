import os
import zlib
import datetime
import functools
import argparse
import json

FRAME_TO_MILLISEC = 42

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
    secs = frame_count * FRAME_TO_MILLISEC / 1000
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


    player_data = get_player_data(decompressed[161: 161 + 432])
    # Get the colours
    TOP_VS_BOTTOM_IDENTIFIER = 15
    print(int.to_bytes(6, length=2, byteorder='little'))
    if int.from_bytes(decompressed[60:62], byteorder='little') != TOP_VS_BOTTOM_IDENTIFIER:
        #TODO this is hardcoded, detect number of players and think of reasonable colours
        # Needs to go to a separete function
        pass
    else:
        for i in range(len(player_data)):
            player_data[i]['colour'] = read_int(buffer=decompressed, start_idx=593 + i*4)

    headers['player_info'] = player_data
    
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


        r = functools.reduce(lambda a,b: a+b, player['player_name'])
        if r:
            player['player_name'] = player['player_name'].decode().strip('\x00')
            player_data.append(player)

    return player_data


def parse(fname):
    with open(fname, 'rb') as f:
        content = f.read()
    
    try:
        check_replay_version(content)
    except Exception as e:
        print(f"Warning: Replay file {fname} is of an older version, skipping...")
        return {}

    headers = parse_replay_header(content)

    return headers

def parse_bytestream(content):
    try:
        check_replay_version(content)
    except Exception as e:
        print(f"Warning: Replay file is of an older version, skipping...")
        return {}

    headers = parse_replay_header(content)

    return headers


def batch_parse(replay_root, batch, print_all):
    output = []
    for path, _, files in os.walk(replay_root):
        if files:
            series_length = 0
            players_series = set()
            for rep in files:
                if not rep.endswith('.rep'):
                    continue
                fname = os.path.join(path, rep)
                parsed = parse(fname)
                if not parsed:
                    # Parsing failed for any reason, e.g., replay was not 1.21
                    continue
                players = set([ x['player_name'] for x in parsed['player_info'] ])
                if batch:
                    series_length += parsed['time_seconds'] 
                    players_series = players_series.union(players)

                if print_all:
                    output.append({'path': fname, 'elapsed_time': parsed['time_formatted'], 'players': players, 'elapsed_time_seconds': parsed['time_seconds']})
                    # output.append(f'{fname}: {parsed["time_formatted"]} {players}')
            
            if series_length and batch:
                #normalise time
                series_duration = datetime.timedelta(seconds=series_length)
                series_duration = str(series_duration).split('.')[0]
                # output.append(f'{path}: {series_duration} {players_series}')
                output.append({'path': path, 'elapsed_time': series_duration, 'players': players_series, 'is_dir': True, 'elapsed_time_seconds': series_length})

    return output

USE_CONFIG = False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SC:R replay statistics")

    parser.add_argument('--rep_root', default='.')
    parser.add_argument('--batch', default=True)
    parser.add_argument('--print_all', default=True)
    args = parser.parse_args()

    if USE_CONFIG:
        if os.path.exists(os.path.join('.', 'config.json')):
            with open('config.json') as f:
                config = json.load(f)

            config = [['--' + k, v] for k, v in config.items() if v and k in args]
            config = functools.reduce(lambda x, y: x + y, config)
            args = parser.parse_args(config, args)
        else:
            print("Config file not found, accepting arguments from cmd line")

    replay_root = args.rep_root
    batch = args.batch
    print_all = args.print_all
    output = batch_parse(replay_root=replay_root, batch=batch, print_all=print_all)
    print(output)
