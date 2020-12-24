import os

from tpDcc.libs.datalibrary.core import datalib


def full_demo():

    current_path = os.path.dirname(__file__)
    db_file = os.path.join(current_path, 'dino.db')
    if os.path.isfile(db_file):
        os.remove(db_file)
    plugin_paths = [os.path.join(current_path, 'plugins')]
    data_lib = datalib.DataLibrary.create(path=db_file, plugin_locations=plugin_paths)

    # Specify where where our data is located
    data_lib.add_scan_location(os.path.join(current_path, 'data'), sync=True)

    # We can search by tags or use the special * wildcard
    for data_identifier in data_lib.find('*'):

        data = data_lib.get(data_identifier)
        print(data.identifier())
        print('\t{}'.format(data))

        for k, v in data.functionality().items():
            print('\t\t{} = {}'.format(k, v))


if __name__ == '__main__':
    full_demo()
