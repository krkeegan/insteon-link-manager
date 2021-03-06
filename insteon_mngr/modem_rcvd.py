import time

from insteon_mngr.trigger import PLMTrigger
from insteon_mngr import BYTE_TO_ID, BYTE_TO_HEX


class ModemRcvdHandler(object):
    '''Provides the generic incomming message handling for the PLM.  Seperate
    class is mostly to make it consistent with other devices.'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device
        # self._last_rcvd_msg = None  # Is this ever used?

    def _rcvd_plm_ack(self, msg):
        if (self._device._last_sent_msg.plm_ack is False and
                msg.raw_msg[0:-1] == self._device._last_sent_msg.raw_msg):
            self._device._last_sent_msg.plm_ack = True
            self._device._last_sent_msg.time_plm_ack = time.time()
        else:
            msg.allow_trigger = False
            print('received spurious plm ack')

    def _rcvd_prelim_plm_ack(self, msg):
        # TODO consider some way to increase allowable ack time
        if (self._device._last_sent_msg.plm_prelim_ack is False and
                self._device._last_sent_msg.plm_ack is False and
                msg.raw_msg[0:-1] == self._device._last_sent_msg.raw_msg):
            self._device._last_sent_msg.plm_prelim_ack = True
        else:
            msg.allow_trigger = False
            print('received spurious prelim plm ack')

    def _rcvd_all_link_manage_ack(self, msg):
        aldb = msg.raw_msg[3:11]
        ctrl_code = msg.get_byte_by_name('ctrl_code')
        link_flags = msg.get_byte_by_name('link_flags')
        search_attributes = {
            'controller': True if link_flags & 0b01000000 else False,
            'responder': True if ~link_flags & 0b01000000 else False,
            'group': msg.get_byte_by_name('group'),
            'dev_addr_hi': msg.get_byte_by_name('dev_addr_hi'),
            'dev_addr_mid': msg.get_byte_by_name('dev_addr_mid'),
            'dev_addr_low': msg.get_byte_by_name('dev_addr_low'),
        }
        self._rcvd_plm_ack(msg)

    def _rcvd_all_link_manage_nack(self, msg):
        print('error writing aldb to PLM, will rescan plm and try again')
        plm = self._device
        self._device._last_sent_msg.failed = True
        self._device.query_aldb()
        trigger_attributes = {
            'plm_cmd': 0x6A,
            'plm_resp': 0x15
        }
        trigger = PLMTrigger(plm=plm, attributes=trigger_attributes)
        dev_addr_hi = msg.get_byte_by_name('dev_addr_hi')
        dev_addr_mid = msg.get_byte_by_name('dev_addr_mid')
        dev_addr_low = msg.get_byte_by_name('dev_addr_low')
        device_id = BYTE_TO_ID(dev_addr_hi, dev_addr_mid, dev_addr_low)
        device = self._device.get_device_by_addr(device_id)
        # TODO these are broken
        if msg.get_byte_by_name('link_flags') == 0xE2:
            plm = self._device.get_object_by_group_num(msg.get_byte_by_name('group'))
            trigger.trigger_function = lambda: plm.send_handler.create_controller_link(device)
        else:
            device = device.get_object_by_group_num(
                msg.get_byte_by_name('group'))
            trigger.trigger_function = lambda: plm.send_handler.create_responder_link(device)
        trigger.name = 'rcvd_all_link_manage_nack'
        trigger.queue()

    def _rcvd_insteon_msg(self, msg):
        insteon_obj = self._device.get_device_by_addr(msg.insteon_msg.from_addr_str)
        if insteon_obj is not None:
            insteon_obj.msg_rcvd(msg)

    def _rcvd_plm_x10_ack(self, msg):
        pass

    def _rcvd_aldb_record(self, msg):
        if (self._device._last_sent_msg.plm_ack is False and
                self._device._last_sent_msg.plm_prelim_ack is True):
            self._device._last_sent_msg.plm_ack = True
            self._device._last_sent_msg.time_plm_ack = time.time()
            self._device.aldb.add_record(msg.raw_msg[2:])
            self._device.send_command('all_link_next_rec')
        else:
            msg.allow_trigger = False
            print('received spurious plm aldb record')

    def _rcvd_end_of_aldb(self, msg):
        # pylint: disable=W0613
        self._device._last_sent_msg.plm_ack = True
        print('reached the end of the PLMs ALDB')
        # Reassign the PLM ALDB keys, they are not permanent
        for link in self._device.get_all_user_links().values():
            if link._adoptable_responder_key() is not None:
                link.set_responder_key(link._adoptable_responder_key())
        for link in self._device.core.get_user_links_for_this_controller_device(self._device).values():
            if link._adoptable_controller_key() is not None:
                link.set_controller_key(link._adoptable_controller_key())
        records = self._device.aldb.get_all_records()
        for key in sorted(records):
            print(key, ":", BYTE_TO_HEX(records[key]))

    def _rcvd_all_link_complete(self, msg):
        if msg.get_byte_by_name('link_code') == 0xFF:
            # DELETE THINGS
            pass
        else:
            # Fix stupid discrepancy in Insteon spec
            link_flag = 0xA2
            if msg.get_byte_by_name('link_code') == 0x01:
                link_flag = 0xE2
            record = bytearray(8)
            record[0] = link_flag
            record[1:8] = msg.raw_msg[3:]
            self._device.aldb.add_record(record)
            # notify the linked device
            device_id = BYTE_TO_ID(record[2], record[3], record[4])
            device = self._device.get_device_by_addr(device_id)
            if msg.get_byte_by_name('link_code') == 0x01:
                dev_cat = msg.get_byte_by_name('dev_cat')
                sub_cat = msg.get_byte_by_name('sub_cat')
                firmware = msg.get_byte_by_name('firmware')
                device.set_dev_version(dev_cat, sub_cat, firmware)

    def _rcvd_btn_event(self, msg):
        # pylint: disable=W0613
        print("The PLM Button was pressed")
        # Currently there is no processing of this event

    def _rcvd_plm_reset(self, msg):
        # pylint: disable=W0613
        self._device.aldb.clear_all_records()
        print("The PLM was manually reset")

    def _rcvd_plm_info(self, msg_obj):
        if (self._device._last_sent_msg.plm_cmd_type == 'plm_info' and
                msg_obj.plm_resp_ack):
            self._device._last_sent_msg.plm_ack = True
            dev_addr_hi = msg_obj.get_byte_by_name('plm_addr_hi')
            dev_addr_mid = msg_obj.get_byte_by_name('plm_addr_mid')
            dev_addr_low = msg_obj.get_byte_by_name('plm_addr_low')
            self._device.set_dev_addr(BYTE_TO_ID(dev_addr_hi,
                                                 dev_addr_mid,
                                                 dev_addr_low))
            dev_cat = msg_obj.get_byte_by_name('dev_cat')
            sub_cat = msg_obj.get_byte_by_name('sub_cat')
            firmware = msg_obj.get_byte_by_name('firmware')
            self._device.set_dev_version(dev_cat, sub_cat, firmware)

    def _rcvd_all_link_clean_status(self, msg):
        if self._device._last_sent_msg.plm_cmd_type == 'all_link_send':
            self._device._last_sent_msg.seq_lock = False
            if msg.plm_resp_ack:
                self._device._last_sent_msg.plm_ack = True
                print('Send All Link - Success')
            elif msg.plm_resp_nack:
                print('Send All Link - Error')
                self._device._last_sent_msg.plm_ack = True
                # We don't resend, instead we rely on individual device
                # alllink cleanups to do the work
                # TODO is the right?  When does a NACK acutally occur?
                # It doesn't seem to happen when a destination device sends a
                # NACK, possibly only when PLM is interrupted, in which case do
                # we want to try and send again?
        else:
            msg.allow_trigger = False
            print('Ignored spurious all link clean status')

    def _rcvd_all_link_clean_failed(self, msg):
        failed_addr = bytearray(3)
        failed_addr[0] = msg.get_byte_by_name('fail_addr_hi')
        failed_addr[1] = msg.get_byte_by_name('fail_addr_mid')
        failed_addr[2] = msg.get_byte_by_name('fail_addr_low')
        fail_device = self._device.get_device_by_addr(BYTE_TO_HEX(failed_addr))
        print('Scene Command Failed, Retrying')
        # TODO We are ignoring the all_link cleanup nacks sent directly
        # by the device, do anything with them?
        cmd = self._device._last_sent_msg.get_byte_by_name('cmd_1')
        fail_device.send_handler.send_all_link_clean(
            msg.get_byte_by_name('group'), cmd)

    def _rcvd_all_link_start(self, msg):
        if msg.plm_resp_ack:
            self._device._last_sent_msg.plm_ack = True

    def _rcvd_x10(self, msg):
        pass
