from insteon.trigger import InsteonTrigger
from insteon.sequences.common import SetALDBDelta, BaseSequence, WriteALDBRecord


class ScanDeviceALDBi1(BaseSequence):
    def start(self):
        self._device.aldb.clear_all_records()
        self._i1_start_aldb_entry_query(0x0F, 0xF8)

    def _i1_start_aldb_entry_query(self, msb, lsb):
        trigger_attributes = {'cmd_2': msb}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='set_address_msb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._send_peek_request(lsb)
        trigger.name = self._device.dev_addr_str + 'query_aldb'
        trigger.queue()
        message = self._device.send_handler.create_message('set_address_msb')
        message.insert_bytes_into_raw({'msb': msb})
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)

    def _get_byte_address(self):
        lsb = self._device.last_sent_msg.get_byte_by_name('cmd_2')
        msb_msg = self._device.search_last_sent_msg(
            insteon_cmd='set_address_msb')
        msb = msb_msg.get_byte_by_name('cmd_2')
        aldb_key = self._device.aldb.get_aldb_key(msb, lsb)
        if self._device.aldb.is_last_aldb(aldb_key):
            self._device.aldb.print_records()
            self._device.remove_state_machine('query_aldb')
            aldb_sequence = SetALDBDelta(self._device)
            aldb_sequence.success_callback = self.success_callback
            aldb_sequence.failure_callback = self.failure_callback
            aldb_sequence.start()
        else:
            dev_bytes = self._device.aldb.get_next_aldb_address(msb, lsb)
            send_handler = self._device.send_handler
            if msb != dev_bytes['msb']:
                send_handler.i1_start_aldb_entry_query(dev_bytes['msb'],
                                                       dev_bytes['lsb'])
            else:
                self._send_peek_request(dev_bytes['lsb'])

    def _send_peek_request(self, lsb):
        trigger = InsteonTrigger(device=self._device,
                                 command_name='peek_one_byte')
        trigger.trigger_function = lambda: self._get_byte_address()
        trigger.name = self._device.dev_addr_str + 'query_aldb'
        trigger.queue()
        message = self._device.send_handler.create_message('peek_one_byte')
        message.insert_bytes_into_raw({'lsb': lsb})
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)


class WriteALDBRecordi1(WriteALDBRecord):
    def __init__(self, device):
        super().__init__(device)
        self._position = 0

    def _perform_write(self):
        # TODO we can skip setting the msb if we can find the last msb
        # requested in the sent message queue
        msb = self.address[0]
        lsb = self.address[1] - 0x07  # i1 devices start at low end
        trigger_attributes = {'cmd_2': msb}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='set_address_msb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._send_peek_request(lsb)
        trigger.name = self._device.dev_addr_str + 'write_aldb'
        trigger.queue()
        message = self._device.send_handler.create_message('set_address_msb')
        message.insert_bytes_into_raw({'msb': msb})
        message.state_machine = 'write_aldb'
        self._device.queue_device_msg(message)

    def _send_peek_request(self, lsb):
        trigger = InsteonTrigger(device=self._device,
                                 command_name='peek_one_byte')
        trigger.trigger_function = lambda: self._send_poke_request(lsb)
        trigger.name = self._device.dev_addr_str + 'write_aldb'
        trigger.queue()
        message = self._device.send_handler.create_message('peek_one_byte')
        message.insert_bytes_into_raw({'lsb': lsb})
        message.state_machine = 'write_aldb'
        self._device.queue_device_msg(message)

    def _addr_byte_by_pos(self, pos):
        msg_attributes = self._compiled_record()
        positions = ['link_flags', 'group', 'dev_addr_hi', 'dev_addr_mid',
                     'dev_addr_low', 'data_1', 'data_2', 'data_3']
        return msg_attributes[positions[pos]]

    def _send_poke_request(self, lsb):
        lsb_byte = self._addr_byte_by_pos(self._position)
        trigger_attributes = {'cmd_2': lsb_byte}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='poke_one_byte',
                                 attributes=trigger_attributes)
        if self._position < 7:
            next_lsb = lsb + 0x01
            callback = lambda: self._send_peek_request(next_lsb)
        else:
            callback = lambda: self._write_complete()
        trigger.trigger_function = callback
        trigger.name = self._device.dev_addr_str + 'write_aldb'
        trigger.queue()
        message = self._device.send_handler.create_message('poke_one_byte')
        message.insert_bytes_into_raw({'lsb': lsb_byte})
        message.state_machine = 'write_aldb'
        self._position += 1
        self._device.queue_device_msg(message)

    def _write_failure(self):
        if self.failure_callback is not None:
            self._failure()

    def _write_complete(self):
        self._device.remove_state_machine('write_aldb')
        aldb_sequence = SetALDBDelta(self._device)
        aldb_sequence.start()