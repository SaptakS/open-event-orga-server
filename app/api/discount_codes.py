from flask_rest_jsonapi import ResourceDetail, ResourceList, ResourceRelationship
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow_jsonapi import fields
from marshmallow import validates_schema
import marshmallow.validate as validate

from app.api.helpers.utilities import dasherize
from flask_jwt import current_identity as current_user, _jwt_required
from app.api.helpers.permissions import jwt_required
from app.api.helpers.errors import ForbiddenError
from sqlalchemy.orm.exc import NoResultFound
from app.models import db
from app.api.bootstrap import api
from app.models.event import Event
from app.models.discount_code import DiscountCode
from app.api.helpers.exceptions import UnprocessableEntity
from app.api.helpers.errors import NotFoundError
from app.api.helpers.db import safe_query


class DiscountCodeSchemaTicket(Schema):
    """
    API Schema for discount_code Model
    """

    class Meta:
        type_ = 'discount-code'
        self_view = 'v1.discount_code_detail'
        self_view_kwargs = {'id': '<id>'}
        inflect = dasherize

    @validates_schema(pass_original=True)
    def validate_quantity(self, data, original_data):
        if 'id' in original_data['data']:
            discount_code = DiscountCode.query.filter_by(id=original_data['data']['id']).one()
            if 'min_quantity' not in data:
                data['min_quantity'] = discount_code.min_quantity

            if 'max_quantity' not in data:
                data['max_quantity'] = discount_code.max_quantity

            if 'tickets_number' not in data:
                data['tickets_number'] = discount_code.tickets_number

        if 'min_quantity' in data or 'max_quantity' in data:
            if data['min_quantity'] >= data['max_quantity']:
                raise UnprocessableEntity({'pointer': '/data/attributes/min-quantity'},
                                          "min-quantity should be less than max-quantity")

        if 'tickets_number' in data or 'max_quantity' in data:
            if data['tickets_number'] < data['min_quantity']:
                    raise UnprocessableEntity({'pointer': '/data/attributes/tickets-number'},
                                              "tickets-number should be greater than min-quantity")

    id = fields.Integer()
    code = fields.Str(allow_none=True)
    discount_url = fields.Url(allow_none=True)
    value = fields.Float(allow_none=True)
    type = fields.Str(validate=validate.OneOf(choices=["amount", "percent"]), allow_none=True)
    is_active = fields.Boolean()
    tickets_number = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    min_quantity = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    max_quantity = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    valid_from = fields.DateTime(allow_none=True)
    valid_till = fields.DateTime(allow_none=True)
    tickets = fields.Str(validate=validate.OneOf(choices=["event", "ticket"]), allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    used_for = fields.Str(allow_none=True)
    event = Relationship(attribute='event',
                         self_view='v1.discount_code_event',
                         self_view_kwargs={'id': '<id>'},
                         related_view='v1.event_detail',
                         related_view_kwargs={'discount_code_id': '<id>'},
                         schema='EventSchema',
                         type_='event')

class DiscountCodeSchemaEvent(Schema):
    """
    API Schema for discount_code Model
    """

    class Meta:
        type_ = 'discount-code'
        self_view = 'v1.discount_code_detail'
        self_view_kwargs = {'id': '<id>'}
        inflect = dasherize

    @validates_schema(pass_original=True)
    def validate_quantity(self, data, original_data):
        if 'id' in original_data['data']:
            discount_code = DiscountCode.query.filter_by(id=original_data['data']['id']).one()
            if 'min_quantity' not in data:
                data['min_quantity'] = discount_code.min_quantity

            if 'max_quantity' not in data:
                data['max_quantity'] = discount_code.max_quantity

            if 'tickets_number' not in data:
                data['tickets_number'] = discount_code.tickets_number

        if 'min_quantity' in data or 'max_quantity' in data:
            if data['min_quantity'] >= data['max_quantity']:
                raise UnprocessableEntity({'pointer': '/data/attributes/min-quantity'},
                                          "min-quantity should be less than max-quantity")

        if 'tickets_number' in data or 'max_quantity' in data:
            if data['tickets_number'] < data['min_quantity']:
                    raise UnprocessableEntity({'pointer': '/data/attributes/tickets-number'},
                                              "tickets-number should be greater than min-quantity")

    id = fields.Integer()
    code = fields.Str(allow_none=True)
    discount_url = fields.Url(allow_none=True)
    value = fields.Float(allow_none=True)
    type = fields.Str(validate=validate.OneOf(choices=["amount", "percent"]), allow_none=True)
    is_active = fields.Boolean()
    tickets_number = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    min_quantity = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    max_quantity = fields.Integer(validate=lambda n: n >= 0, allow_none=True)
    valid_from = fields.DateTime(allow_none=True)
    valid_till = fields.DateTime(allow_none=True)
    tickets = fields.Str(validate=validate.OneOf(choices=["event", "ticket"]), allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    used_for = fields.Str(allow_none=True)
    events = Relationship(attribute='event',
                         self_view='v1.discount_code_event',
                         self_view_kwargs={'id': '<id>'},
                         related_view='v1.event_list',
                         related_view_kwargs={'discount_code_id': '<id>'},
                         schema='EventSchema',
                         type_='event')

class DiscountCodeList(ResourceList):
    """
    List and Create Discount Code
    """

    def query(self, view_kwargs):
        """
        query method for Discount Code List
        :param view_kwargs:
        :return:
        """
        query_ = self.session.query(DiscountCode)
        if view_kwargs.get('event_id') and current_user.is_co_organizer(view_kwargs.get('event_id')):
            event = safe_query(self, Event, 'id', view_kwargs['event_id'], 'event_id')
            query_ = query_.filter_by(event_id=event.id)
            self.schema = DiscountCodeSchemaTicket

        elif view_kwargs.get('event_identifier') and current_user.is_co_organizer(view_kwargs.get('event_id')):
            event = safe_query(self, Event, 'identifier', view_kwargs['event_identifier'], 'event_identifier')
            query_ = query_.join(Event).filter(Event.id == event.id)
            self.schema = DiscountCodeSchemaTicket

        elif (not view_kwargs.get('event_identifier') or not view_kwargs.get('event_id')) and current_user.is_admin:
            self.schema = DiscountCodeSchemaEvent
        else:
            raise UnprocessableEntity({'source': ''},"Neither Admin nor Organizer")

        return query_

    def before_create_object(self, data, view_kwargs):
        """
        Method to create object before posting
        :param data:
        :param view_kwargs:
        :return:
        """
        if view_kwargs.get('event_id') and data['used_for'] == 'ticket' and current_user.is_organizer(view_kwargs.get('event_id')):
            print "hello"
            self.schema = DiscountCodeSchemaTicket
            event = safe_query(self, Event, 'id', view_kwargs['event_id'], 'event_id')
            data['event_id'] = event.id
            try:
                self.session.query(DiscountCode).filter_by(event_id=data['event_id']).filter_by(used_for='event').one()
            except NoResultFound:
                pass
            else:
                raise UnprocessableEntity({'parameter': 'event_id'},
                                      "Discount Code already exists for the provided Event ID")

        elif view_kwargs.get('event_identifier') and data['used_for'] == 'ticket' and current_user.is_organizer(view_kwargs.get('event_id')):
            print "hello"
            self.schema = DiscountCodeSchemaTicket
            event = safe_query(self, Event, 'identifier', view_kwargs['event_identifier'], 'event_identifier')
            data['event_id'] = event.id
            try:
                self.session.query(DiscountCode).filter_by(event_id=data['event_id']).filter_by(used_for='event').one()
            except NoResultFound:
                pass
            else:
                raise UnprocessableEntity({'parameter': 'event_identifier'},
                                      "Discount Code already exists for the provided Event ID")

        elif not view_kwargs.get('event_identifier') and not view_kwargs.get('event_id') and data['used_for'] == 'ticket':
            raise UnprocessableEntity({'source': ''},"Use /v1/events/<int:event_id/discout-codes endpoint")

        elif (not view_kwargs.get('event_identifier') or not view_kwargs.get('event_id'))\
        and data['used_for'] == 'event' and current_user.is_admin:
            print "hey", current_user.is_admin
            self.schema = DiscountCodeSchemaEvent

        elif (view_kwargs.get('event_identifier') or view_kwargs.get('event_id')) and data['used_for'] == 'event':
            raise UnprocessableEntity({'source': ''},"Use /v1/discout-codes endpoint")

        else:
            raise UnprocessableEntity({'source': ''},"Please check used_for and endpoint and verify your permission")

    decorators = (jwt_required,)
    schema = DiscountCodeSchemaEvent
    data_layer = {'session': db.session,
                  'model': DiscountCode,
                  'methods': {
                    'query': query,
                    'before_create_object': before_create_object}}


class DiscountCodeDetail(ResourceDetail):
    """
    Discount Code detail by id
    """

    def before_get_object(self, view_kwargs):
        """
        query method for Discount Code List
        :param view_kwargs:
        :return:
        """
        print view_kwargs['id']
        discount = self.session.query(DiscountCode).filter_by(id=view_kwargs.get('id'))
        if not discount:
            raise NotFoundError()

        if discount.used_for == 'ticket' and current_user.is_co_organizer(discount.event_id):
            self.schema = DiscountCodeSchemaTicket

        elif discount.used_for == 'event' and current_user.is_admin:
            self.schema = DiscountCodeSchemaEvent
        else:
            raise UnprocessableEntity({'source': ''},"Neither Admin nor Organizer")

    def before_update_object(self, obj, data, view_kwargs):
        """
        Method to create object before posting
        :param data:
        :param view_kwargs:
        :return:
        """
        discount = self.session.query(DiscountCode).filter_by(id=view_kwargs.get('id'))
        if not discount:
            raise NotFoundError()

        if 'used_for' in data:
            used_for = data['used_for']

        if discount.used_for == 'ticket' and current_user.is_co_organizer(discount.event_id) and used_for != 'event':
            print "hello"
            self.schema = DiscountCodeSchemaTicket

        elif data['used_for'] == 'event' and current_user.is_admin and used_for != 'ticket':
            print "hey", current_user.is_admin
            self.schema = DiscountCodeSchemaEvent

        else:
            raise UnprocessableEntity({'source': ''},"Please check used_for and endpoint and verify your permission")

    decorators = (jwt_required,)
    schema = DiscountCodeSchemaEvent
    data_layer = {'session': db.session,
                  'model': DiscountCode,
                  'methods': {
                    'before_get_object': before_get_object,
                    'before_update_object': before_update_object}}


class DiscountCodeRelationship(ResourceRelationship):
    """
    Discount Code Relationship
    """
    decorators = (jwt_required,)
    schema = DiscountCodeSchemaEvent
    data_layer = {'session': db.session,
                  'model': DiscountCode}
