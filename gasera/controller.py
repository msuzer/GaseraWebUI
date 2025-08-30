from typing import Optional
from .protocol import GaseraProtocol, DeviceStatus, ErrorList, TaskList, ACONResult, MeasurementStatus, DeviceName, IterationNumber, NetworkSettings, DateTimeResult
from .protocol import DeviceInfo, SelfTestResult, TaskParameters, SystemParameters, SamplerParameters, ParameterValue
from .config import get_gas_name, get_color_for_cas
from .tcp_client import tcp_client

class GaseraController:
    class TaskList:
        CALIBRATION_TASK = "7"
        DEFAULT = "11"
        FLUSH = "12"
        MTEST2 = "13"

        # Mapping of task name → numeric ID (both as strings)
        NAME_TO_ID = {
            "Calibration Task": CALIBRATION_TASK,
            "DEFAULT": DEFAULT,
            "FLUSH": FLUSH,
            "MTEST2": MTEST2,
        }

        @classmethod
        def all_ids(cls):
            return set(cls.NAME_TO_ID.values())

        @classmethod
        def all_names(cls):
            return set(cls.NAME_TO_ID.keys())

    def __init__(self):
        self.proto = GaseraProtocol()
    
    def check_device_connection(self):
        was_online = getattr(self, "_was_online", None)
        is_now = tcp_client.is_online()
        if was_online != is_now:
            print(f"[INFO] Gasera is now {'online' if is_now else 'offline'}")
        self._was_online = is_now
        return is_now

    def acon_proxy(self) -> dict:
        command = GaseraProtocol().build_command("ACON")
        response = tcp_client.send_command(command)
        if response is not None:
            acon_result = GaseraProtocol().parse_acon(response)
            if acon_result:
                return {
                    "timestamp": acon_result.timestamp,
                    "readable": acon_result.readable_time,
                    "components": [
                        {
                            "cas": rec.cas,
                            "ppm": rec.ppm,
                            "label": f"{get_gas_name(rec.cas)} ({rec.cas})" if get_gas_name(rec.cas) else rec.cas,
                            "color": get_color_for_cas(rec.cas)
                        } for rec in acon_result.records
                    ]
                }
        return {"error": "Failed to parse ACON"}

    def get_device_status(self) -> Optional[DeviceStatus]:
        cmd = self.proto.ask_current_status()
        resp = tcp_client.send_command(cmd)
        if resp:
            result = self.proto.parse_asts(resp)
            if tcp_client.on_status_change:
                tcp_client.on_status_change(result)
            return result
        return None

    def get_active_errors(self) -> Optional[ErrorList]:
        cmd = self.proto.ask_active_errors()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_aerr(resp) if resp else None

    def get_task_list(self) -> Optional[TaskList]:
        cmd = self.proto.ask_task_list()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_atsk(resp) if resp else None

    def start_measurement(self, task_id: str = TaskList.DEFAULT) -> Optional[str]:
        if task_id not in TaskList.all_ids():
                return None

        cmd = self.proto.start_measurement_by_id(task_id)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "STAM").as_string() if resp else None

    def stop_measurement(self) -> Optional[str]:
        cmd = self.proto.stop_measurement()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "STPM").as_string() if resp else None

    def get_last_results(self) -> Optional[ACONResult]:
        cmd = self.proto.get_last_measurement_results()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_acon(resp) if resp else None

    def get_measurement_status(self) -> Optional[MeasurementStatus]:
        cmd = self.proto.get_measurement_status()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_amst(resp) if resp else None

    def get_device_name(self) -> Optional[DeviceName]:
        cmd = self.proto.get_device_name()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_anam(resp) if resp else None
    
    def get_device_info(self) -> Optional[str]:
        cmd = self.proto.get_device_info()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_adev(resp).as_string() if resp else None

    def get_iteration_number(self) -> Optional[IterationNumber]:
        cmd = self.proto.get_iteration_number()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_aitr(resp) if resp else None

    def get_network_settings(self) -> Optional[NetworkSettings]:
        cmd = self.proto.get_network_settings()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_anet(resp) if resp else None

    def get_device_time(self) -> Optional[DateTimeResult]:
        cmd = self.proto.get_device_datetime()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_aclk(resp) if resp else None

    def set_component_order(self, cas_list: str) -> Optional[str]:
        cmd = self.proto.set_component_order(cas_list)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "SCOR").as_string() if resp else None

    def set_concentration_format(self, show_time: int, show_cas: int, show_conc: int, show_inlet: int = -1) -> Optional[str]:
        cmd = self.proto.set_concentration_format(show_time, show_cas, show_conc, show_inlet)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "SCON").as_string() if resp else None

    def start_measurement_by_name(self, task_name: str) -> Optional[str]:
        if task_name not in TaskList.all_names():
            return None
    
        cmd = self.proto.start_measurement_by_name(task_name)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "STAT").as_string() if resp else None

    def set_network_settings(self, use_dhcp: int, ip: str, netmask: str, gw: str) -> Optional[str]:
        cmd = self.proto.set_network_settings(use_dhcp, ip, netmask, gw)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "SNET").as_string() if resp else None

    def get_parameter(self, name: str) -> Optional[str]:
        cmd = self.proto.get_parameter(name)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_apar(resp).as_string() if resp else None

    def set_online_mode(self, enable: bool) -> Optional[str]:
        cmd = self.proto.set_online_mode(enable)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "SONL").as_string() if resp else None

    def set_laser_tuning_interval(self, interval: int) -> Optional[str]:
        cmd = self.proto.set_laser_tuning_interval(interval)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "STUN").as_string() if resp else None

    def get_task_parameters(self, task_id: int) -> Optional[str]:
        cmd = self.proto.get_task_parameters(task_id)
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_atsp(resp).as_string() if resp else None

    def get_system_parameters(self) -> Optional[str]:
        cmd = self.proto.get_system_parameters()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_asyp(resp).as_string() if resp else None

    def get_sampler_parameters(self) -> Optional[str]:
        cmd = self.proto.get_sampler_parameters()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_amps(resp).as_string() if resp else None

    def start_self_test(self) -> Optional[str]:
        cmd = self.proto.start_self_test()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "STST").as_string() if resp else None

    def get_self_test_result(self) -> Optional[str]:
        cmd = self.proto.get_self_test_result()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_astr(resp).as_string() if resp else None

    def reboot_device(self) -> Optional[str]:
        cmd = self.proto.reboot_device()
        resp = tcp_client.send_command(cmd)
        return self.proto.parse_generic(resp, "RDEV").as_string() if resp else None

# lazy singleton instance
gasera = GaseraController()