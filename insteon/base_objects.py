import time
import datetime
import pprint
import binascii
from insteon.user_link import UserLink


def BYTE_TO_HEX(data):
    '''Takes a bytearray or a byte and returns a string
    representation of the hex value'''
    return binascii.hexlify(data).decode().upper()

def BYTE_TO_ID(high, mid, low):
    # pylint: disable=E1305
    ret = ('{:02x}'.format(high, 'x').upper() +
           '{:02x}'.format(mid, 'x').upper() +
           '{:02x}'.format(low, 'x').upper())
    return ret

def ID_STR_TO_BYTES(dev_id_str):
    ret = bytearray(3)
    ret[0] = (int(dev_id_str[0:2], 16))
    ret[1] = (int(dev_id_str[2:4], 16))
    ret[2] = (int(dev_id_str[4:6], 16))
    return ret

# This is here because the above functions are imported in these
# consider some other structure to avoid what is clearly a bad import
from insteon.devices import (GroupSendHandler, GroupFunctions)

class Group(object):
    '''The base class.  All groups inherit this, the root group gets a lot more
    functions.  Specialized groups can modify or add functions in classes that
    inherit this.'''
    def __init__(self, root, group_number, **kwargs):
        self._root = root
        self._group_number = group_number
        self._attributes = {}
        if 'attributes' in kwargs and kwargs['attributes'] is not None:
            self._load_attributes(kwargs['attributes'])
        self.send_handler = GroupSendHandler(self)
        self.functions = GroupFunctions(self)

    @property
    def group_number(self):
        return self._group_number

    @property
    def root(self):
        return self._root

    @property
    def state(self):
        '''Returns the cached state of the device.'''
        return self.attribute('state')

    @state.setter
    def state(self, value):
        self.attribute(attr='state', value=value)
        self.attribute(attr='state_time', value=time.time())

    @property
    def state_age(self):
        '''Returns the age in seconds of the state value.'''
        return time.time() - self.attribute('state_time')

    @property
    def name(self):
        name = self.attribute('name')
        if name is None:
            name = ''
        return name

    @name.setter
    def name(self, value):
        return self.attribute('name', value)

    def _load_attributes(self, attributes):
        for name, value in attributes.items():
            self.attribute(name, value)

    def _get_undefined_responder(self):
        ret = []
        attributes = {
            'responder': True,
            'group': self.group_number,
            'dev_addr_hi': self.root.dev_addr_hi,
            'dev_addr_mid': self.root.dev_addr_mid,
            'dev_addr_low': self.root.dev_addr_low
        }
        aldb_responder_links = self.root.core.get_matching_aldb_records(attributes)
        for aldb_link in aldb_responder_links:
            if (len(aldb_link.get_reciprocal_records()) == 0 and
                aldb_link.is_a_defined_link() is False):
                # A responder link exists on the device, this will be listed
                # in the undefined controller function
                ret.append(aldb_link)
        return ret

    def _get_undefined_controller(self):
        ret = []
        attributes = {
            'controller': True,
            'group': self.group_number
        }
        aldb_controller_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if (aldb_link.is_a_defined_link() is False and
                aldb_link.linked_device is not None):
                ret.append(aldb_link)
        return ret

    def attribute(self, attr, value=None):
        if value is not None:
            self._attributes[attr] = value
        try:
            ret = self._attributes[attr]
        except KeyError:
            ret = None
        return ret

    def get_undefined_links(self):
        ret = []
        # 1 Undefined Controllers on This Device
        ret.extend(self._get_undefined_controller())
        # 2 Orphaned Undefined Responders on Other Devices
        ret.extend(self._get_undefined_responder())
        return ret

    def get_unknown_device_links(self):
        '''Returns all links on the device which do not associated with a
        known device'''
        ret = []
        attributes = {
            'controller': True,
            'group': self.group_number
        }
        aldb_controller_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        attributes = {
            'responder': True,
            'data_3': self.group_number
        }
        aldb_responder_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_responder_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        return ret

    def get_attributes(self):
        return self._attributes.copy()

class Root(Group):
    '''The root object of an insteon device, inherited by Devices and Modems'''
    def __init__(self, core, plm, **kwargs):
        self._core = core
        self._plm = plm
        self._state_machine = 'default'
        self._state_machine_time = 0
        self._device_msg_queue = {}
        self._out_history = []
        self._id_bytes = bytearray(3)
        self._groups = []
        self._user_links = []
        if 'device_id' in kwargs:
            self._id_bytes = ID_STR_TO_BYTES(kwargs['device_id'])
        super().__init__(self, 0x01, **kwargs)

    @property
    def dev_addr_hi(self):
        return self._id_bytes[0]

    @property
    def dev_addr_mid(self):
        return self._id_bytes[1]

    @property
    def dev_addr_low(self):
        return self._id_bytes[2]

    @property
    def dev_addr_str(self):
        ret = BYTE_TO_HEX(
            bytes([self.dev_addr_hi, self.dev_addr_mid, self.dev_addr_low]))
        return ret

    @property
    def dev_cat(self):
        dev_cat = self.attribute('dev_cat')
        if dev_cat is None:
            dev_cat = 0x00
        return dev_cat

    @property
    def sub_cat(self):
        sub_cat = self.attribute('sub_cat')
        if sub_cat is None:
            sub_cat = 0x00
        return sub_cat

    @property
    def firmware(self):
        firmware = self.attribute('firmware')
        if firmware is None:
            firmware = 0x00
        return firmware

    @property
    def engine_version(self):
        return self.attribute('engine_version')

    @property
    def core(self):
        return self._core

    @property
    def plm(self):
        return self._plm

    @property
    def state_machine(self):
        '''The state machine tracks the 'state' that the device is in.
        This is necessary because Insteon is not a stateless protocol,
        interpreting some incoming messages requires knowing what
        commands were previously issued to the device.

        Whenever a state is set, only messages of that state will be
        sent to the device, all other messages will wait in a queue.
        To avoid locking up a device, a state will automatically be
        eliminated if it has not been updated within 8 seconds. You
        can update a state by calling update_state_machine or sending
        a command with the appropriate state value'''
        if self._state_machine_time <= (time.time() - 8) or \
                self._state_machine == 'default':
            # Always check for states other than default
            if self._state_machine != 'default':
                now = datetime.datetime.now().strftime("%M:%S.%f")
                print(now, self._state_machine, "state expired")
                pprint.pprint(self._device_msg_queue)
            self._state_machine = self._get_next_state_machine()
            if self._state_machine != 'default':
                self._state_machine_time = time.time()
        return self._state_machine

    @property
    def user_links(self):
        '''This returns a dictionary like what we see in config.json'''
        ret = None
        if self.attribute('user_links') is not None:
            ret = {}
            records = self.attribute('user_links')
            for device in records.keys():
                ret[device] = {}
                for group in records[device].keys():
                    ret[device][int(group)] = records[device][group]
        return ret

    @user_links.setter
    def user_links(self, records):
        self.attribute('user_links', records)

    ##################################
    # Private functions
    ##################################

    def _get_next_state_machine(self):
        next_state = 'default'
        msg_time = 0
        for state in self._device_msg_queue:
            if state != 'default' and self._device_msg_queue[state]:
                test_time = self._device_msg_queue[state][0].creation_time
                if test_time and (msg_time == 0 or test_time < msg_time):
                    next_state = state
                    msg_time = test_time
        return next_state

    def _resend_msg(self, message):
        state = message.state_machine
        if state not in self._device_msg_queue:
            self._device_msg_queue[state] = []
        self._device_msg_queue[state].insert(0, message)
        self._state_machine_time = time.time()

    def _update_message_history(self, msg):
        # Remove old messages first
        archive_time = time.time() - 120
        last_msg_to_del = 0
        for search_msg in self._out_history:
            if search_msg.time_sent < archive_time:
                last_msg_to_del += 1
            else:
                break
        if last_msg_to_del:
            del self._out_history[0:last_msg_to_del]
        # Add this message onto the end
        self._out_history.append(msg)

    def _load_user_links(self, links):
        for controller_id, groups in links.items():
            for group_number, all_data in groups.items():
                for data in all_data:
                    self._user_links.append(UserLink(
                        self,
                        controller_id,
                        group_number,
                        data
                    ))

    ##################################
    # Public functions
    ##################################

    def remove_state_machine(self, value):
        if value == self.state_machine:
            print('finished', self.state_machine)
            self._state_machine = 'default'
            self._state_machine_time = time.time()
        else:
            print(value, 'was not the active state_machine')

    def update_state_machine(self, value):
        if value == self.state_machine:
            self._state_machine_time = time.time()
        else:
            print(value, 'was not the active state_machine')

    def queue_device_msg(self, message):
        if message.state_machine not in self._device_msg_queue:
            self._device_msg_queue[message.state_machine] = []
        self._device_msg_queue[message.state_machine].append(message)

    def pop_device_queue(self):
        '''Returns and removes the next message in the queue'''
        ret = None
        if self.state_machine in self._device_msg_queue and \
                self._device_msg_queue[self.state_machine]:
            ret = self._device_msg_queue[self.state_machine].pop(0)
            self._update_message_history(ret)
            self._state_machine_time = time.time()
        return ret

    def next_msg_create_time(self):
        '''Returns the creation time of the message to be sent in the queue'''
        ret = None
        try:
            ret = self._device_msg_queue[self.state_machine][0].creation_time
        except (KeyError, IndexError):
            pass
        return ret

    def search_last_sent_msg(self, **kwargs):
        '''Return the most recently sent message of this type
        plm_cmd or insteon_cmd'''
        ret = None
        if 'plm_cmd' in kwargs:
            for msg in reversed(self._out_history):
                if msg.plm_cmd_type == kwargs['plm_cmd']:
                    ret = msg
                    break
        elif 'insteon_cmd' in kwargs:
            for msg in reversed(self._out_history):
                if msg.insteon_msg and \
                      msg.insteon_msg.device_cmd_name == kwargs['insteon_cmd']:
                    ret = msg
                    break
        return ret

    def create_group(self, group_num, group, attributes=None):
        if group_num > 0x01 and group_num <= 0xFF:
            self._groups.append(group(self, group_num, attributes=attributes))

    def get_object_by_group_num(self, search_num):
        ret = None
        if search_num == 0x00 or search_num == 0x01:
            ret = self
        else:
            for group_obj in self._groups:
                if group_obj.group_number == search_num:
                    ret = group_obj
                    break
        return ret

    def get_all_groups(self):
        return self._groups.copy()

    def set_dev_addr(self, addr):
        self._id_bytes = ID_STR_TO_BYTES(addr)
        return

    def set_dev_version(self, dev_cat=None, sub_cat=None, firmware=None):
        self.attribute('dev_cat', dev_cat)
        self.attribute('sub_cat', sub_cat)
        self.attribute('firmware', firmware)
        self.update_device_classes()
        return

    def update_device_classes(self):
        # pylint: disable=R0201
        return NotImplemented

    def export_links(self):
        # pylint: disable=E1101
        records = {}
        # TODO improve to use ALDB Record classes
        for key in self.aldb.get_all_records().keys():
            parsed = self.aldb.parse_record(key)
            if parsed['in_use'] and not parsed['controller']:
                linked_record = self.aldb.get_record(key)
                linked_root = linked_record.linked_device.root
                name = linked_record.get_linked_device_str()
                group = parsed['group']
                group = 0x01 if group == 0x00 else group
                if group == 0x01 and linked_root is self.plm:
                    # ignore i2cs required links
                    continue
                if name not in records.keys():
                    records[name] = {}
                if group not in records[name].keys():
                    records[name][group] = []
                for entry in records[name][group]:
                    # ignore duplicates
                    if (entry['data_1'] == parsed['data_1'] and
                            entry['data_2'] == parsed['data_2'] and
                            entry['data_3'] == parsed['data_3']):
                        continue
                records[name][group].append({
                    'data_1': parsed['data_1'],
                    'data_2': parsed['data_2'],
                    'data_3': parsed['data_3']
                })
        if self.user_links is not None:
            new_records = records
            records = self.user_links
            records.update(new_records)
        self.user_links = records
