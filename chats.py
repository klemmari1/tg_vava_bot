from dataclasses import dataclass

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


@dataclass
class Chat(db.Model):
    id: int

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)

    def __repr__(self):
        return "<Chat %r>" % self.id

    def subscribe(self):
        db.session.add(self)
        db.session.commit()

    def unsubscribe(self):
        db.session.delete(self)
        db.session.commit()
