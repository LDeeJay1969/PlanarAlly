import auth
from app import app, logger, sio, state
from models import Label, LabelSelection, User
from models.db import db


@sio.on("Label.Add", namespace="/planarally")
@auth.login_required(app, sio)
async def add(sid, data):
    sid_data = state.sid_map[sid]
    user = sid_data["user"]
    room = sid_data["room"]
    location = sid_data["location"]

    label = Label.get_or_none(uuid=data)

    if label is not None:
        logger.warn(f"{user.name} tried to add a label with an id that already exists.")
        return

    if data["user"] != user.name:
        logger.warn(f"{user.name} tried to add a label for someone else.")
        return

    data["user"] = User.by_name(data["user"])
    label = Label.create(**data)

    for psid in state.get_sids(skip_sid=sid, room=room):
        if state.get_user(psid) == user or label.visible:
            await sio.emit(
                "Label.Add", label.as_dict(), room=psid, namespace="/planarally"
            )


@sio.on("Label.Delete", namespace="/planarally")
@auth.login_required(app, sio)
async def delete(sid, data):
    sid_data = state.sid_map[sid]
    user = sid_data["user"]
    room = sid_data["room"]
    location = sid_data["location"]

    label = Label.get_or_none(uuid=data)

    if label is None:
        logger.warn(f"{user.name} tried to delete a non-existing label.")
        return

    if label.user != user:
        logger.warn(f"{user.name} tried to delete another user's label.")
        return

    label.delete_instance(True)

    await sio.emit(
        "Label.Delete",
        {"user": user.name, "uuid": data},
        skip_sid=sid,
        namespace="/planarally",
    )


@sio.on("Label.Visibility.Set", namespace="/planarally")
@auth.login_required(app, sio)
async def set_visibility(sid, data):
    sid_data = state.sid_map[sid]
    user = sid_data["user"]
    room = sid_data["room"]
    location = sid_data["location"]

    label = Label.get_or_none(uuid=data["uuid"])

    if label is None:
        logger.warn(f"{user.name} tried to change a non-existing label.")
        return

    if label.user != user:
        logger.warn(f"{user.name} tried to change another user's label.")
        return

    label.visible = data["visible"]
    label.save()

    for psid in state.get_sids(skip_sid=sid, room=room):
        if state.get_user(psid) == user:
            await sio.emit(
                "Label.Visibility.Set",
                {"user": label.user.name, **data},
                room=psid,
                namespace="/planarally",
            )
        else:
            if data["visible"]:
                await sio.emit(
                    "Label.Add", label.as_dict(), room=psid, namespace="/planarally"
                )
            else:
                await sio.emit(
                    "Label.Delete", {'uuid': label.uuid, 'user': label.user.name}, room=psid, namespace="/planarally"
                )


@sio.on("Labels.Filter.Add", namespace="/planarally")
@auth.login_required(app, sio)
async def add_filter(sid, uuid):
    sid_data = state.sid_map[sid]
    user = sid_data["user"]
    room = sid_data["room"]

    label = Label.get_or_none(uuid=uuid)

    LabelSelection.create(label=label, user=user, room=room)

    for psid in state.get_sids(skip_sid=sid, room=room):
        if state.get_user(psid) == user:
            await sio.emit("Labels.Filter.Add", uuid, room=psid, namespace="/planarally")


@sio.on("Labels.Filter.Remove", namespace="/planarally")
@auth.login_required(app, sio)
async def remove_filter(sid, uuid):
    sid_data = state.sid_map[sid]
    user = sid_data["user"]
    room = sid_data["room"]

    label = Label.get_or_none(uuid=uuid)

    ls = LabelSelection.get_or_none(label=label, room=room, user=user)

    if ls:
        ls.delete_instance(True)

    for psid in state.get_sids(skip_sid=sid, room=room):
        if state.get_user(psid) == user:
            await sio.emit("Labels.Filter.Remove", uuid, room=psid, namespace="/planarally")
