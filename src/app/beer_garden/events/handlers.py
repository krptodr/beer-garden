# -*- coding: utf-8 -*-
import logging

from brewtils import models as brewtils_models
from brewtils.models import Event, Events, Request
from mongoengine import NotUniqueError

import beer_garden.config
import beer_garden.db.api as db
import beer_garden.garden
import beer_garden.router
from beer_garden.local_plugins.manager import PluginManager
import beer_garden.requests

logger = logging.getLogger(__name__)


def garden_callbacks(event: Event) -> None:
    """Callbacks for events

    Args:
        event: The event

    Returns:
        None
    """

    if event.name in (Events.SYSTEM_CREATED.name,):
        beer_garden.garden.garden_add_system(event.payload, event.garden)

    if event.name in (
        Events.GARDEN_CREATED.name,
        Events.GARDEN_STARTED.name,
        Events.GARDEN_UPDATED.name,
    ):
        # Only accept local garden updates and the garden sending the event
        # This should prevent grand-child gardens getting into the database

        if (
            event.payload.name == event.garden
            and event.payload.name != beer_garden.config.get("garden.name")
        ):
            garden = beer_garden.garden.get_garden(event.payload.name)
            if garden is None:
                beer_garden.garden.create_garden(event.payload)

    elif event.name in (Events.GARDEN_REMOVED.name,):
        # Only accept local garden updates and the garden sending the event
        # This should prevent grand-child gardens getting into the database
        if event.payload.name in [event.garden, beer_garden.config.get("garden.name")]:
            beer_garden.router.remove_garden(event.payload)

    # Subset of events we only care about if they originate from the local garden
    if event.garden == beer_garden.config.get("garden.name"):
        if event.error:
            logger.error(f"Local error event ({event}): {event.error_message}")
            return

        try:
            # Start local plugins after the entry point comes up
            if event.name == Events.ENTRY_STARTED.name:
                PluginManager.start_all()
            elif event.name == Events.INSTANCE_INITIALIZED.name:
                PluginManager.handle_associate(event)
            elif event.name == Events.INSTANCE_STARTED.name:
                PluginManager.handle_start(event)
            elif event.name == Events.INSTANCE_STOPPED.name:
                PluginManager.handle_stop(event)
            elif event.name == Events.SYSTEM_REMOVED.name:
                PluginManager.handle_remove_system(event)
            elif event.name == Events.SYSTEM_RESCAN_REQUESTED.name:
                new_plugins = PluginManager.instance().load_new()

                for runner_id in new_plugins:
                    PluginManager.start_one(runner_id)
        except Exception as ex:
            logger.exception(f"Error executing local callback for {event}: {ex}")

    # Subset of events we only care about if they originate from a downstream garden
    else:
        if event.error:
            logger.error(f"Downstream error event: {event!r}")
            return

        if event.name in (
            Events.REQUEST_CREATED.name,
            Events.REQUEST_STARTED.name,
            Events.REQUEST_UPDATED.name,
            Events.REQUEST_COMPLETED.name,
        ):
            record = db.query_unique(Request, id=event.payload.id)

            if record:
                event.payload.has_parent = record.has_parent
                event.payload.parent = record.parent

        if event.name in (Events.REQUEST_CREATED.name, Events.SYSTEM_CREATED.name):
            try:
                db.create(event.payload)
            except NotUniqueError:
                logger.error(
                    f"Error processing {event.name}: object already exists ({event!r})"
                )

        elif event.name in (
            Events.REQUEST_STARTED.name,
            Events.REQUEST_COMPLETED.name,
            Events.SYSTEM_UPDATED.name,
            Events.INSTANCE_UPDATED.name,
        ):
            if not event.payload_type:
                logger.error(
                    f"Error processing {event.name}: no payload type ({event!r})"
                )
                return

            model_class = getattr(brewtils_models, event.payload_type)
            record = db.query_unique(model_class, id=event.payload.id)

            if record:
                db.update(event.payload)
            else:
                logger.error(
                    f"Error processing {event.name}: object does not exist ({event!r})"
                )

        elif event.name in (Events.SYSTEM_REMOVED.name,):

            if not event.payload_type:
                logger.error(
                    f"Error processing {event.name}: no payload type ({event!r})"
                )
                return

            model_class = getattr(brewtils_models, event.payload_type)
            record = db.query_unique(model_class, id=event.payload.id)

            if record:
                db.delete(event.payload)
            else:
                logger.error(
                    f"Error processing {event.name}: object does not exist ({event!r})"
                )
