# coding=utf-8
import json
from pydux import create_store
import unittest

from badgecheck.actions.action_types import ADD_TASK
from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.reducers import main_reducer
from badgecheck.state import filter_active_tasks, INITIAL_STATE
from badgecheck.tasks import task_named
from badgecheck.tasks.validation import (_get_validation_actions, detect_and_validate_node_class, OBClasses,
                                         PrimitiveValueValidator, validate_id_property, validate_primitive_property,
                                         ValueTypes,)
from badgecheck.tasks.task_types import (VALIDATE_ID_PROPERTY,
                                         VALIDATE_PRIMITIVE_PROPERTY,
                                         DETECT_AND_VALIDATE_NODE_CLASS, IDENTITY_OBJECT_PROPERTY_DEPENDENCIES)
from badgecheck.verifier import call_task

from testfiles.test_components import test_components

class PropertyValidationTests(unittest.TestCase):

    def test_data_uri_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.DATA_URI)
        good_uris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=',
                     'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==',
                     'data:text/plain;charset=UTF-8;page=21,the%20data:1234,5678',
                     'data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh',
                     'data:,actually%20a%20valid%20data%20URI',
                     'data:,')
        bad_uris = ('data:image/gif',
                    'http://someexample.org',
                    'data:bad:path')
        for uri in good_uris:
            self.assertTrue(validator(uri), u"`{}` should pass data URI validation but failed.".format(uri))
        for uri in bad_uris:
            self.assertFalse(validator(uri), u"`{}` should fail data URI/URL validation but passed.".format(uri))

    def test_data_uri_or_url_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.DATA_URI_OR_URL)
        good_uris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=',
                     'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==',
                     'data:text/plain;charset=UTF-8;page=21,the%20data:1234,5678',
                     'data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh',
                     'http://www.example.com:8080/', 'http://www.example.com:8080/foo/bar',
                     'http://www.example.com/foo%20bar', 'http://www.example.com/foo/bar?a=b&c=d',
                     'http://www.example.com/foO/BaR', 'HTTPS://www.EXAMPLE.cOm/',
                     'http://142.42.1.1:8080/', 'http://142.42.1.1/',
                     'http://foo.com/blah_(wikipedia)#cite-1', 'http://a.b-c.de',
                     'http://userid:password@example.com/', "http://-.~:%40:80%2f:password@example.com",
                     'http://code.google.com/events/#&product=browser')
        bad_uris = ('///', '///f', '//',
                    'rdar://12345', 'h://test', 'http:// shouldfail.com', ':// should fail', '', 'a',
                    'urn:uuid:129487129874982374', 'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72')
        for uri in good_uris:
            self.assertTrue(validator(uri), u"`{}` should pass data URI/URL validation but failed.".format(uri))
        for uri in bad_uris:
            self.assertFalse(validator(uri), u"`{}` should fail data URI/URL validation but passed.".format(uri))

    def test_url_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.URL)
        # Thanks to Mathias Bynens for fun URL examples: http://mathiasbynens.be/demo/url-regex
        good_urls = ('http://www.example.com:8080/', 'http://www.example.com:8080/foo/bar',
                     'http://www.example.com/foo%20bar', 'http://www.example.com/foo/bar?a=b&c=d',
                     'http://www.example.com/foO/BaR', 'HTTPS://www.EXAMPLE.cOm/',
                     'http://142.42.1.1:8080/', 'http://142.42.1.1/',
                     'http://foo.com/blah_(wikipedia)#cite-1', 'http://a.b-c.de',
                     'http://userid:password@example.com/', "http://-.~:%40:80%2f:password@example.com",
                     'http://code.google.com/events/#&product=browser')
        good_urls_that_fail = (u'http://✪df.ws/123', u'http://عمان.icom.museum/',)  # TODO: Discuss support for these
        bad_urls = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=', '///', '///f', '//',
                    'rdar://12345', 'h://test', 'http:// shouldfail.com', ':// should fail', '', 'a',
                    'urn:uuid:129487129874982374', 'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72')
        bad_urls_that_pass = ('http://', 'http://../', 'http://foo.bar?q=Spaces should be encoded',
                                          'http://f', 'http://-error-.invalid/', 'http://.www.foo.bar./',)

        for url in good_urls:
            self.assertTrue(validator(url), u"`{}` should pass URL validation but failed.".format(url))
        for url in bad_urls:
            self.assertFalse(validator(url), u"`{}` should fail URL validation but passed.".format(url))

    def test_iri_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.IRI)
        # Thanks to Mathias Bynens for fun URL examples: http://mathiasbynens.be/demo/url-regex
        good_iris = ('http://www.example.com:8080/', '_:b0', '_:b12', '_:b107', '_:b100000001232',
                     'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72',
                     'urn:uuid:9D278beb-36cf-4bc8-888d-674ff9843d72'
                     )
        good_iris_that_fail = ()  # TODO: Discuss support for these
        bad_iris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=', 'urn:uuid', 'urn:uuid:123',
                    '', 'urn:uuid:', 'urn:uuid:zz278beb-36cf-4bc8-888d-674ff9843d72',)
        bad_iris_that_pass = ()

        for url in good_iris:
            self.assertTrue(validator(url), u"`{}` should pass IRI validation but failed.".format(url))
        for url in bad_iris:
            self.assertFalse(validator(url), u"`{}` should fail IRI validation but passed.".format(url))


class PropertyValidationTaskTests(unittest.TestCase):

    def test_basic_text_property_validation(self):
        first_node = {'id': 'http://example.com/1', 'string_prop': 'string value'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='string_prop',
            prop_type=ValueTypes.TEXT,
            required=False
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        task['required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        first_node['string_prop'] = 1
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop value 1 not valid in unknown type node {}".format(first_node['id'])
        )

        task['required'] = False
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Optional string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop value 1 not valid in unknown type node {}".format(first_node['id'])
        )

        # When property isn't present
        second_node = {'id': 'http://example.com/1'}
        state = {'graph': [second_node]}
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")

        task['required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")

    def test_basic_boolean_property_validation(self):
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='bool_prop',
            required=False,
            prop_type=ValueTypes.BOOLEAN
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")
        self.assertEqual(
            message, "Optional property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        task['required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")
        self.assertEqual(
            message, "Required property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        first_node['bool_prop'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required boolean property matches expectation")
        self.assertEqual(
            message, "BOOLEAN property bool_prop valid in unknown type node {}".format(first_node['id'])
        )

    def test_basic_id_validation(self):
        ## test assumes that a node's ID must be an IRI
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='id',
            required=True,
            prop_type=ValueTypes.IRI
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 0)

    def test_basic_image_prop_validation(self):
        _VALID_DATA_URI = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=='
        _VALID_IMAGE_URL = 'http://example.com/images/foo.png'
        _INVALID_URI = 'notanurl'
        first_node = {'id': 'http://example.com/1',
                      'image_prop': _VALID_DATA_URI}

        state = {
            'graph': [first_node]
        }

        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='image_prop',
            required=False,
            prop_type=ValueTypes.DATA_URI_OR_URL
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional image_prop URI is present and well-formed; validation should pass.")
        self.assertEqual(
            message, "DATA_URI_OR_URL property image_prop valid in unknown type node {}".format(first_node['id'])
        )

        first_node['image_prop'] = _INVALID_URI
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Optional image prop is present and mal-formed; validation should fail.")
        self.assertEqual(
            message, "DATA_URI_OR_URL property image_prop value {} not valid in unknown type node {}".format(
                _INVALID_URI,
                first_node['id'])
        )

    def test_basic_url_prop_validation(self):
        _VALID_URL = 'http://example.com/2'
        _INVALID_URL = 'notanurl'
        first_node = {'id': 'http://example.com/1',
                      'url_prop': _VALID_URL}
        state = {
            'graph': [first_node]
        }

        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='url_prop',
            required=False,
            prop_type=ValueTypes.URL
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional URL prop is present and well-formed; validation should pass.")
        self.assertEqual(
            message, "URL property url_prop valid in unknown type node {}".format(first_node['id'])
        )

        first_node['url_prop'] = _INVALID_URL
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Optional URL prop is present and mal-formed; validation should fail.")
        self.assertEqual(
            message, "URL property url_prop value {} not valid in unknown type node {}".format(
                _INVALID_URL,
                first_node['id'])
        )

    def test_basic_datetime_property_validation(self):
        _VALID_DATETIMES = ['1977-06-10T12:00:00+0800',
                            '1977-06-10T12:00:00-0800',
                            '1977-06-10T12:00:00+08',
                            '1977-06-10T12:00:00+08:00']
        _INVALID_NOTZ_DATETIMES = ['1977-06-10T12:00:00']
        _INVALID_DATETIMES = ['notadatetime']

        first_node = {'id': 'http://example.com/1', 'date_prop': '1977-06-10T12:00:00Z'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='date_prop',
            required=False,
            prop_type=ValueTypes.DATETIME
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional date prop is present and well-formed; validation should pass.")
        self.assertEqual(
            message, "DATETIME property date_prop valid in unknown type node {}".format(first_node['id'])
        )

        for date in _VALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertTrue(result,
                            "Optional date prop {} is well-formed; validation should pass.".format(date))
            self.assertEqual(
                message, "DATETIME property date_prop valid in unknown type node {}".format(first_node['id'])
            )

        for date in _INVALID_NOTZ_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertFalse(result, "Optional date prop has no tzinfo particle; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop value {} not valid in unknown type node {}".format(
                    str(date), first_node['id'])
            )

        for date in _INVALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertFalse(result, "Optional date prop has malformed datetime; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop value {} not valid in unknown type node {}".format(
                    str(date), first_node['id'])
            )

    def test_validation_action(self):
        store = create_store(main_reducer, INITIAL_STATE)
        first_node = {
            'text_prop': 'text_value',
            'bool_prop': True
        }
        store.dispatch(add_node(node_id="http://example.com/1", data=first_node))

        # 0. Test of an existing valid text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="text_prop",
            required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 1. Test of an missing optional text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_text_prop",
            required=False,
            prop_type=ValueTypes.TEXT
        ))

        # 2. Test of an present optional valid boolean prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            required=False,
            prop_type=ValueTypes.BOOLEAN
        ))

        # 3. Test of a present invalid text prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 4. Test of a required missing boolean prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_bool_prop",
            required=True,
            prop_type=ValueTypes.BOOLEAN
        ))

        # TODO refactor while loop into callable here and in badgecheck.verifier.verify()
        last_task_id = 0
        while len(filter_active_tasks(store.get_state())):
            active_tasks = filter_active_tasks(store.get_state())
            task_meta = active_tasks[0]
            task_func = task_named(task_meta['name'])

            if task_meta['id'] == last_task_id:
                break

            last_task_id = task_meta['id']
            call_task(task_func, task_meta, store)

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 5)
        self.assertTrue(state['tasks'][0]['success'], "Valid required text property is present.")
        self.assertTrue(state['tasks'][1]['success'], "Missing optional text property is OK.")
        self.assertTrue(state['tasks'][2]['success'], "Valid optional boolean property is present.")
        self.assertFalse(state['tasks'][3]['success'], "Invalid required text property is present.")
        self.assertFalse(state['tasks'][4]['success'], "Required boolean property is missing.")

    def optional_accepts_null_values(self):
        """
        If a simple or id-type property is optional, null values should not be rejected.
        """
        pass
        # TODO: they should be filtered from the node reported at output.

    def test_many_validation(self):
        """
        When detect_and_validate_node_class (through _get_validation_actions)
        queue up actions, some configs may have many=True. This means single or multiple
        values should be accepted. If optional, empty lists should also be accepted.
        """
        first_node = {
            'id': '_:b0',
            'type': 'BadgeClass'
        }
        state = {'graph': [first_node]}
        required = True

        good_values = (
            (['one', 'two', 'three'], "Multiple text values should be acceptable"),
            ('one', "Single text value should be acceptable"),
        )
        optional_prop_good_values = (
            ([], "For Optional many=True props, empty lists should {}"),
            (None, "For optional many=True props, single null value should {}"),
            ([None], "For optional many=True props, list with an empty value should {}"),
            ([None, None], "For optional many=True props, list with only empty values should {}"),
            ([None, "one"], "For optional many=True props, list with an empty value should {}"),
        )
        bad_values = (
            (1, "Single non-text value should fail"),
            (["one", 2, "three"], "Non-text value in a list should fail"),
        )

        def run(expect_success, msg):
            task = add_task(
                VALIDATE_PRIMITIVE_PROPERTY, node_id=first_node['id'], node_class=OBClasses.BadgeClass,
                prop_name='tags', prop_type=ValueTypes.TEXT, required=required, many=True
            )
            result, message, actions = validate_primitive_property(state, task)
            self.assertEqual(result, expect_success, msg)

        for val, error_message in good_values:
            first_node['tags'] = val
            run(True, error_message)

        for val, error_message in bad_values:
            first_node['tags'] = val
            run(False, error_message)

        required = True
        for val, error_message in optional_prop_good_values:
            first_node['tags'] = val
            run(False, error_message.format('fail when prop is required'))

        required = False
        for val, error_message in optional_prop_good_values:
            first_node['tags'] = val
            run(True, error_message.format('pass when prop is not required'))


class IDPropertyValidationTests(unittest.TestCase):
    def test_validate_nested_identity_object(self):
        first_node = {
            'id': 'http://example.com/1',
            'recipient': '_:b0'
        }
        second_node = {
            'id': '_:b0',
            'identity': 'two@example.com',
            'type': 'email',
            'hashed': False
        }
        state = {'graph': [first_node, second_node]}

        task = add_task(
            VALIDATE_ID_PROPERTY,
            node_id="http://example.com/1",
            prop_name="recipient",
            required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.IdentityObject
        )

        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.IdentityObject)

    def test_validate_linked_related_resource(self):
        first_node = {
            'id': 'http://example.com/1',
            'badge': 'http://example.com/2'
        }
        state = {'graph': [first_node]}

        task = add_task(
            VALIDATE_ID_PROPERTY,
            node_id="http://example.com/1",
            prop_name="badge",
            required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.BadgeClass,
            fetch=True
        )

        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.BadgeClass)

    def test_many_validation_for_id_property(self):
        """
        When detect_and_validate_node_class (through _get_validation_actions)
        queue up actions, some configs may have many=True. This means single or multiple
        values should be accepted. If optional, empty lists should also be accepted.
        """
        first_node = {
            'id': '_:b0',
            'type': 'Assertion'
        }
        second_node = {
            'id': '_:b1',
            'narrative': 'Did cool stuff'
        }
        third_node = {
            'id': '_:b2',
            'narrative': 'Did more cool stuff'
        }
        state = {'graph': [first_node, second_node, third_node]}
        required = True

        task = add_task(
            VALIDATE_ID_PROPERTY, node_id=first_node['id'], node_class=OBClasses.Assertion,
            prop_name='evidence', prop_type=ValueTypes.ID, required=required, many=True, fetch=False,
            expected_class=OBClasses.Evidence, allow_remote_url=True
        )
        result, message, actions = validate_id_property(state, task)
        self.assertFalse(result)
        self.assertTrue('Required property evidence not present' in message)

        first_node['evidence'] = 'http://youtube.com/avideoofmedoingthething'
        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "A single string URL value should be acceptable for evidence")
        self.assertTrue('reference is' in message, "Message should properly report single property entry")

        first_node['evidence'] = 'notanurl'
        result, message, actions = validate_id_property(state, task)
        self.assertFalse(result, "A single string value that doesn't look like a URL is not acceptable as evidence")

        first_node['evidence'] = ['http://example.com/1', 'http://example.com/2']
        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "Multiple string URLs should be acceptable for evidence")
        self.assertTrue('references are' in message, "Message should properly report plural references.")

        first_node['evidence'] = ['_:b1', 'http://example.com/2']
        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "An embedded node and a URL should be acceptable evidence references")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['node_id'], '_:b1')


class NodeTypeDetectionTasksTests(unittest.TestCase):
    def detect_assertion_type_from_node(self):
        node_data = json.loads(test_components['2_0_basic_assertion'])
        state = {'graph': [node_data]}
        task = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=node_data['id'])

        result, message, actions = detect_and_validate_node_class(state, task)
        self.assertTrue(result, "Type detection task should complete successfully.")
        self.assertEqual(len(actions), 5)

        issuedOn_task = [t for t in actions if t['prop_name'] == 'issuedOn'][0]
        self.assertEqual(issuedOn_task['prop_type'], ValueTypes.DATETIME)


class ClassValidationTaskTests(unittest.TestCase):
    def test_validate_identity_object_property_dependencies(self):
        first_node = {
            'id': 'http://example.com/1',
            'recipient': '_:b0'
        }
        second_node = {
            'id': '_:b0',
            'identity': 'sha256$c7ef86405ba71b85acd8e2e95166c4b111448089f2e1599f42fe1bba46e865c5',
            'type': 'email',
            'hashed': True,
            'salt': 'deadsea'
        }
        state = {'graph': [first_node, second_node]}

        task = add_task(
            VALIDATE_ID_PROPERTY,
            node_id="http://example.com/1",
            prop_name="recipient",
            prop_required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.IdentityObject
        )

        def run(cur_state, cur_task, expected_result, msg=''):
            result, message, actions = validate_id_property(cur_state, cur_task)
            self.assertTrue(result, "Property validation task should succeed.")
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]['expected_class'], OBClasses.IdentityObject)

            cur_task = actions[0]
            result, message, actions = task_named(cur_task['name'])(cur_state, cur_task)
            self.assertTrue(result, "IdentityObject validation task discovery should succeed.")

            for cur_task in [a for a in actions if a.get('type') == ADD_TASK]:
                val_result, val_message, val_actions = task_named(cur_task['name'])(cur_state, cur_task)
                if not cur_task['name'] == IDENTITY_OBJECT_PROPERTY_DEPENDENCIES:
                    self.assertTrue(val_result, "Test {} should pass".format(cur_task['name']))
                else:
                    self.assertEqual(val_result, expected_result,
                                     "{} should be {}: {}".format(cur_task['name'], expected_result, msg))

        # Hashed and salted
        run(state, task, True, "Good working hashed identity")

        # Identity shouldn't look hashed if it says it isn't!
        second_node['hashed'] = False
        run(state, task, False, "Identity looks hashed and smells fishy")

        # Hash doesn't match known types.
        second_node['hashed'] = True
        second_node['identity'] = "sha1billiion$abc123"
        run(state, task, False, "Hash doesn't match known types")
        second_node['identity'] = "plaintextjane@example.com"
        run(state, task, False, "Identity shouldn't look like email if hashed is true")