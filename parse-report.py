#!/usr/bin/env python

from datetime import datetime
from pymongo import MongoClient
import json
import os

from strat.parse import parse_league_daily, parse_game_daily
from strat.utils import get_report_type, get_title, flatten
from strat.utils import REPORT_TYPE_LEAGUE_DAILY, REPORT_TYPE_GAME_DAILY

CITIES = [
    'Atlanta',
    'Boston',
    'Charlotte',
    'Chicago',
    'Cincinnati',
    'Cleveland',
    'Columbus',
    'Detroit',
    'Miami',
    'Montreal',
    'Nashville',
    'New Orleans',
    'New York',
    'Philadelphia',
    'St. Louis',
    'Saint Louis',
    'Steel City',
    'Washington'
]

NICKNAMES = [
    'Crackers',
    'Blues',
    'Monarchs',
    'Northsiders',
    'Steamers',
    'Spiders',
    'Explorers',
    'Clutch',
    'Toros',
    'Souterrains',
    'Cats',
    'Mudbugs',
    'Knights',
    'Admirals',
    'Clydesdales',
    'Stogies',
    'Federals'
]

HOF_CITIES = [
    'Mt. Washington',
    'Mudville',
    'Sirk City',
    'Hackensack',
    'Motor City',
    'Cook County',
    'Vegas',
    'New Milan'
]

HOF_NICKNAMES = [
    'Wonders',
    'Grey Eagles',
    'Spikes',
    'Monuments',
    'Bulls',
    'Robber Barons',
    'Sultans',
    'Rajahs'
]


def report_type_string(report_type):
    if report_type == REPORT_TYPE_GAME_DAILY:
        return 'game-daily'
    elif report_type == REPORT_TYPE_LEAGUE_DAILY:
        return 'league-daily'
    else:
        return 'unknown'

def main(filename, stash_directory=None, use_db=False, skip_clean=False, league='blb'):
    should_stash = stash_directory is not None

    if league == 'blb':
        cities = CITIES
        nicknames = NICKNAMES
    elif league == 'hof':
        cities = HOF_CITIES
        nicknames = HOF_NICKNAMES
    
    with open(filename, 'r') as f:
        html = f.read()

    report_type = get_report_type(html)
    if report_type == REPORT_TYPE_LEAGUE_DAILY:
        ast = parse_league_daily(html, cities=cities, nicknames=nicknames)
    elif report_type == REPORT_TYPE_GAME_DAILY:
        ast = parse_game_daily(html, cities=cities, nicknames=nicknames)
    else:
        return

    if not skip_clean:
        flat_ast = flatten(ast)

    if use_db:
        client = MongoClient('mongodb://localhost:27017')
        db = client.get_database('extractor')
        collection = db.reports

        document = {'filename': os.path.basename(filename),
                    'subject': '',
                    'content': html,
                    'type': report_type,
                    'ast': ast
        }

        if not skip_clean:
            document['flat_ast'] = flat_ast
            
        collection.insert_one(document)
        client.close()
        
    if should_stash:
        rootname = os.path.splitext(os.path.basename(filename))[0]
        matchup_datetime = datetime.strptime(flat_ast['boxscores'][0]['matchup']['date'], '%m/%d/%Y')
        dst_filename = '{}-{}-{}-ast.dat'.format(
            matchup_datetime.strftime('%Y-%m-%d'),
            report_type_string(report_type),
            rootname
        )
        full_path = os.path.join(stash_directory, dst_filename)
        stash_ast = ast if skip_clean else flat_ast
        with open(full_path, 'w') as f:
            json.dump(stash_ast, f, indent=2)

    if not should_stash and not use_db:
        stash_ast = ast if skip_clean else flat_ast
        print json.dumps(stash_ast, indent=2)
        

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="League daily parser for Strat-O-Matic Report files")
    parser.add_argument('--stash', nargs='?', dest='dir',
                        help='directory to dump ASTs to')
    parser.add_argument('--skip-clean', action='store_true', default=False,
                        help='don\'t clean the AST before writing')
    parser.add_argument('--use-db', action='store_true', default=False,
                        help='insert AST into a database')
    parser.add_argument('--league', choices=['blb', 'hof'], default='blb',
                        help='league the data belongs to')
    parser.add_argument('file', metavar="FILE", help="the input file to parse")
    args = parser.parse_args()
    
    main(args.file, args.dir, args.use_db, args.skip_clean, args.league)
