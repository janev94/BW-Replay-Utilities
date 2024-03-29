import os
import zlib
import datetime
import functools
import argparse
import json

FRAME_TO_MILLISEC = 42
PLAYER_SLOTS = 12 # 8 players + 4 observers

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
    # for our sake we can ignore the first 16 bytes, as these identify the replay file and we only support 1.21+ for now
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

    for i in range(len(player_data)):

        colour = read_int(buffer=decompressed, start_idx=593 + i*4)
        print(f'Reading {i}: {colour}')
        player_data[i]['colour'] = read_int(buffer=decompressed, start_idx=593 + i*4)

    headers['player_info'] = player_data
    
    return headers


def get_player_data(player_buffer):
    player_data = []

    # MAX_PLAYERS = 8
    PLAYER_CHUNK_SIZE = len(player_buffer) // PLAYER_SLOTS

    for i in range(PLAYER_SLOTS):
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


def _find_unique(file_bytes, unique_bytes):
    first_index = file_bytes.find(unique_bytes, 0)
    if first_index == -1:
        return -1
    second_index = file_bytes.find(unique_bytes, first_index + 1)
    if second_index != -1:
        raise Exception("expected unique bytes are not unique")
    return first_index


def replace_colours(byte_content):
    colour_name_to_hex = {
        "red": [0xf5, 0xf4, 0x74, 0x3f, 0x81, 0x80, 0x80, 0x3c, 0x81, 0x80, 0x80, 0x3c, 0x00, 0x00, 0x80, 0x3f],
        "blue": [0xc1, 0xc0, 0x40, 0x3d, 0x91, 0x90, 0x90, 0x3e, 0xcd, 0xcc, 0x4c, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "teal": [0xb1, 0xb0, 0x30, 0x3e, 0xb5, 0xb4, 0x34, 0x3f, 0x95, 0x94, 0x14, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "purple": [0x89, 0x88, 0x08, 0x3f, 0x81, 0x80, 0x80, 0x3e, 0x9d, 0x9c, 0x1c, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "orange": [0xf9, 0xf8, 0x78, 0x3f, 0x8d, 0x8c, 0x0c, 0x3f, 0xa1, 0xa0, 0xa0, 0x3d, 0x00, 0x00, 0x80, 0x3f],
        "brown": [0xe1, 0xe0, 0xe0, 0x3e, 0xc1, 0xc0, 0x40, 0x3e, 0xa1, 0xa0, 0xa0, 0x3d, 0x00, 0x00, 0x80, 0x3f],
        "white": [0xcd, 0xcc, 0x4c, 0x3f, 0xe1, 0xe0, 0x60, 0x3f, 0xd1, 0xd0, 0x50, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "yellow": [0xfd, 0xfc, 0x7c, 0x3f, 0xfd, 0xfc, 0x7c, 0x3f, 0xe1, 0xe0, 0x60, 0x3e, 0x00, 0x00, 0x80, 0x3f],
        "green": [0x81, 0x80, 0x00, 0x3d, 0x81, 0x80, 0x00, 0x3f, 0x81, 0x80, 0x00, 0x3d, 0x00, 0x00, 0x80, 0x3f],
        "pale_yellow": [0xfd, 0xfc, 0x7c, 0x3f, 0xfd, 0xfc, 0x7c, 0x3f, 0xf9, 0xf8, 0xf8, 0x3e, 0x00, 0x00, 0x80, 0x3f],
        "tan": [0xed, 0xec, 0x6c, 0x3f, 0xc5, 0xc4, 0x44, 0x3f, 0xb1, 0xb0, 0x30, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "pale_green": [0xe9, 0xe8, 0xe8, 0x3e, 0xa5, 0xa4, 0x24, 0x3f, 0xf9, 0xf8, 0xf8, 0x3e, 0x00, 0x00, 0x80, 0x3f],
        "blueish_grey": [0xe5, 0xe4, 0xe4, 0x3e, 0x91, 0x90, 0x10, 0x3f, 0xb9, 0xb8, 0x38, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "cyan": [0x00, 0x00, 0x00, 0x00, 0xe5, 0xe4, 0x64, 0x3f, 0xfd, 0xfc, 0x7c, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "pink": [0x00, 0x00, 0x80, 0x3f, 0xc5, 0xc4, 0x44, 0x3f, 0xe5, 0xe4, 0x64, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "olive": [0x81, 0x80, 0x00, 0x3f, 0x81, 0x80, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3f],
        "lime": [0xd3, 0xd2, 0x52, 0x3f, 0xf6, 0xf5, 0x75, 0x3f, 0xf1, 0xf0, 0x70, 0x3e, 0x00, 0x00, 0x80, 0x3f],
        "navy": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x81, 0x80, 0x00, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "dark_aqua": [0x81, 0x80, 0x80, 0x3e, 0xd1, 0xd0, 0xd0, 0x3e, 0xd5, 0xd4, 0x54, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "magenta": [0xf1, 0xf0, 0x70, 0x3f, 0xc9, 0xc8, 0x48, 0x3e, 0xe7, 0xe6, 0x66, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "grey": [0x81, 0x80, 0x00, 0x3f, 0x81, 0x80, 0x00, 0x3f, 0x81, 0x80, 0x00, 0x3f, 0x00, 0x00, 0x80, 0x3f],
        "black": [0xf1, 0xf0, 0x70, 0x3e, 0xf1, 0xf0, 0x70, 0x3e, 0xf1, 0xf0, 0x70, 0x3e, 0x00, 0x00, 0x80, 0x3f]
    }


    #TODO: Redundant
    compressed_hdr = is_zlib_compressed(byte_content[32:])

    if compressed_hdr:
        decompressed = zlib.decompress(byte_content[32:32+633])
    else:
        decompressed = byte_content[32:]

    TOP_VS_BOTTOM_IDENTIFIER = 15
    if int.from_bytes(decompressed[60:62], byteorder='little') != TOP_VS_BOTTOM_IDENTIFIER:
        # 2) find first occurrence of CCLR and verify it's the ONLY occurrence
        # 3) skip the next 4 bytes (section length)
        # 4) skip the next 4 bytes (checksum) but remember their position as we'll be replacing...
        # 5) skip the next 4 bytes (chunk count) but note should always be 1
        # 6) skip the next 4 bytes (compressed size) but remember their position as we'll be replacing...
        
        colour_id_index = _find_unique(byte_content, bytes('CCLR','UTF-8'))
        colour_section_length_index = colour_id_index + 4
        colour_checksum_index = colour_section_length_index + 4
        colour_compressed_size_index = colour_checksum_index + 4 + 4
        colour_compressed_bytes_index = colour_compressed_size_index + 4

        colour_section_length = read_int(buffer=byte_content, start_idx=colour_section_length_index)
        colour_compressed_length = read_int(buffer=byte_content, start_idx=colour_compressed_size_index)

        colour_bytes_compressed = byte_content[colour_compressed_bytes_index: colour_compressed_bytes_index + colour_compressed_length]
        colour_bytes_decompressed = zlib.decompress(colour_bytes_compressed)

        colour_bytes_decompressed_mut = bytearray(colour_bytes_decompressed)

        for i in range(PLAYER_SLOTS):
            # Set everybody to yellow, UMS-like
            colour_bytes_decompressed_mut[i*16: i*16 + 16] = colour_name_to_hex['yellow']

        players_data = get_player_data(decompressed[161: 161 + 432])
        #TODO: Fix later
        # make the players with odd index orange, the player with even index blue
        for i, player_data in enumerate(players_data):
            if i % 2 == 0:
                colour_to_set = colour_name_to_hex['blue']
            else:
                colour_to_set = colour_name_to_hex['orange']
            player_colour_index = player_data['slot_id']
            colour_bytes_decompressed_mut[player_colour_index*16: player_colour_index*16 + 16] = colour_to_set

        # Calculate New Checksum
        new_checksum = int("0b" + "1" * 32, 2) - zlib.crc32(colour_bytes_decompressed_mut)

        new_colour_bytes_compressed = zlib.compress(colour_bytes_decompressed_mut)

        new_compressed_length = len(new_colour_bytes_compressed)

        new_section_length = colour_section_length + new_compressed_length - colour_compressed_length

        new_byte_content = bytearray(byte_content)

        # Update the checksum
        new_byte_content[colour_checksum_index: colour_checksum_index + 4] = new_checksum.to_bytes(length=4, byteorder='little')

        # Update the section length
        new_byte_content[colour_section_length_index: colour_section_length_index + 4] = new_section_length.to_bytes(length=4, byteorder='little')

        # Update the compressed length
        new_byte_content[colour_compressed_size_index: colour_compressed_size_index + 4] = new_compressed_length.to_bytes(length=4, byteorder='little')

        # Remove the old colour content
        del(new_byte_content[colour_compressed_bytes_index: colour_compressed_bytes_index + colour_compressed_length])

        # Insert the new colour content
        new_byte_content[colour_compressed_bytes_index:0] = new_colour_bytes_compressed


        return new_byte_content
    

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
    import sys
    if len(sys.argv) == 1:
        print(parse(''))
        with open('', 'rb') as f:
            content = f.read()
        
        new_content = replace_colours(content)

        with open('', 'wb') as f:
            f.write(new_content)

        sys.exit()
    
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
