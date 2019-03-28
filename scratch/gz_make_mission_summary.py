import pandas as pd

xls = pd.ExcelFile('~/Downloads/GZ Missions.xlsx')

data = xls.parse(sheet_name=0, header=0)

# Region| Mission Type | Mission Name |
regions = data['Region']
regions = list(regions.unique())

mission_types = data['Mission Type']
mission_types = list(mission_types.unique())


region_order = ['Archipelago Region / Southeastern Ostertorn']
mission_type_order = ['Main', 'Side']

for region in region_order:
    print('\n=={}=='.format(region))
    for mt in mission_types:
        print("\n'''{} Missions'''".format(mt))
        for index, row in data.loc[(data['Region'] == region) & (data['Mission Type'] == mt)].iterrows():
            print('\n[[{}]]'.format(row['Mission Name']))

# ==Archipelago Region / Southeastern Ostertorn==
# '''Main Missions'''
#
# [[Break of Dawn]]
#
# [[Sanctuary]]
#
# [[The Farm]]
#
# [[The Road to Salthamn]]
#
# [[The Home Team]]
#
# '''Side Missions'''
#
# [[Old Bettan]]
#
# [[The Hunter]]
#
# [[Shooting Practice]]
