import collections
import sqlite3


class Table(collections.namedtuple('Table', ('name', 'key', 'keysize'))):
    __slots__ = ()

    def _table_exists(self, db):
        return bool(db.execute(
            'SELECT name '
            'FROM sqlite_master '
            'WHERE type = "table" AND name = ?',
            (self.name,)
        ).fetchall())

    def ensure_table_exists(self, db):
        if not self._table_exists(db):
            db.execute(
                'CREATE TABLE {table_info.name} (\n'
                '    {table_info.key} CHAR({table_info.keysize}),\n'
                '    pokemon INT NOT NULL,\n'
                '    lat FLOAT NOT NULL,\n'
                '    lng FLOAT NOT NULL,\n'
                '    expires_at_ms INT NOT NULL,\n'
                '    PRIMARY KEY ({table_info.key}, expires_at_ms)\n'
                ')'.format(table_info=self),
            )

    def insert_data(self, db, data):
        query_fmt = 'INSERT OR REPLACE INTO {name} VALUES (?, ?, ?, ?, ?)'
        db.executemany(query_fmt.format(name=self.name), data)

    def select_non_expired(self, db, current_time_ms):
        return db.execute(
            'SELECT * FROM {} WHERE expires_at_ms > ?'.format(self.name),
            (current_time_ms,)
        ).fetchall()


DATA = Table('data', 'spawn_id', 12)
LURE_DATA = Table('lure_data', 'pokestop_id', 35)


def connect_db():
    return sqlite3.connect('database.db')
