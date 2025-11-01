import heapq
import random
import time
from collections import defaultdict
import uuid
import math # For math.ceil

class Config:
    SIM_DAYS = 7
    SIM_MINUTES_PER_DAY = 24 * 60
    TICK_INTERVAL_MINUTES = 5
    SIM_START_TIME = 0
    SIM_END_TIME = SIM_DAYS * SIM_MINUTES_PER_DAY

    # Patient Generation (Default/Base values - will be overridden by specific hospital configs)
    PATIENT_ARRIVAL_RATE = 0.40 

    # Staff Costs per minute
    PHYSICIAN_COST = 3.0
    NURSE_COST = 1.0
    TECH_COST = 0.50
    RADIOLOGIST_COST = 2.5
    TRANSPORT_COST = 0.60
    VOLUNTEER_COST = 0.0
    OVERTIME_MULTIPLIER = 1.5

    # Consolidated Staffing and Capacity (Default/Base values)
    UNIT_CAPACITY = {
        'ED': 45,
        'INPATIENT': 165,
        'CDU': 0, 
        'IMAGING_CT': 2,
        'IMAGING_MRI': 1,
        'LAB': 5,
        'RADIOLOGY': 1,
    }
    STAFF_PER_UNIT = {
        'ED': {'NURSE': 14, 'PHYSICIAN': 8},
        'INPATIENT': {'NURSE': 30, 'PHYSICIAN': 7},
        'CDU': {'NURSE': 4, 'PHYSICIAN': 1},
        'RADIOLOGY': {'RADIOLOGIST': 6},
        'IMAGING_CT': {'TECH': 6},
        'IMAGING_MRI': {'TECH': 4},
        'LAB': {'TECH': 5}
    }
    TRANSPORT_STAFF = 25 # Base paid transport staff
    VOLUNTEER_TRANSPORT_STAFF = 0 # Base volunteers
    VOLUNTEER_TRANSFER_PROCESS_TIME = (20, 40)
    VOLUNTEER_ACUITY_ELIGIBILITY = ['URGENT_OBS', 'NON_URGENT']
    VOLUNTEER_HOURS_START = 8 * 60
    VOLUNTEER_HOURS_END = 17 * 60

    # Automated Pulley System (Default/Base values)
    PULLEY_SYSTEM_CAPACITY = 0 
    PULLEY_TRANSFER_PROCESS_TIME = (5, 10)
    PULLEY_ELIGIBLE_UNITS = ['ED']
    PULLEY_ELIGIBLE_DESTINATIONS = ['IMAGING_CT', 'IMAGING_MRI']

    INPATIENT_BEDS = 165 # Base inpatient beds

    CDU_BEDS = 20
    CDU_CRITERIA_MATCH = 0.80
    CDU_OBSERVATION_TIME = (10 * 60, 20 * 60)

    IMAGING_PROCESSING_TIME = {
        'CT': (10, 20),
        'MRI': (20, 40)
    }
    IMAGING_REPORTING_TIME = {
        'ROUTINE': (120, 360),
        'CRITICAL': (60, 120)
    }

    LAB_PROCESSING_TIME = (60, 180)

    AI_ENABLED_IMAGING = False # Default to False
    AI_CRITICAL_REDUCTION = 0.30
    AI_ROUTINE_PRELIM_REDUCTION = 0.15
    AI_STAFFING_EFFICIENCY_GAIN = 0.15
    AI_STAFFING_ADJUSTMENT_INTERVAL_MINUTES = 60
    AI_DISCHARGE_REDUCTION = 0.10 # NEW: 10% reduction in discharge process time if AI Staffing enabled

    PATIENT_ACUITY = {
        'CRITICAL': 0.10,
        'URGENT_ADMIT': 0.20,
        'URGENT_OBS': 0.30,
        'NON_URGENT': 0.40
    }
    TRANSPORT_PRIORITY = {
        'CRITICAL': 1,
        'URGENT_ADMIT': 2,
        'URGENT_OBS': 3,
        'NON_URGENT': 4
    }

    ED_TRIAGE_TIME = (10, 30)
    ED_PHYSICIAN_ASSESSMENT_TIME = {
        'CRITICAL': (30, 60),
        'URGENT_ADMIT': (20, 45),
        'URGENT_OBS': (15, 30),
        'NON_URGENT': (10, 20)
    }

    INPATIENT_STAY_TIME = {
        'CRITICAL': (int(2.5 * 24 * 60), int(6 * 24 * 60)),
        'URGENT_ADMIT': (int(1.5 * 24 * 60), int(4 * 24 * 60)),
        'URGENT_OBS': (int(0.8 * 24 * 60), int(2.5 * 24 * 60)),
        'NON_URGENT': (int(0.8 * 24 * 60), int(2.5 * 24 * 60)),
    }
    DISCHARGE_PROCESS_TIME = (90, 150)
    TRANSFER_PROCESS_TIME = (15, 30)

    INPATIENT_CDU_CHECK_INTERVAL = 30

    AMENITIES_ENABLED = False
    AMENITIES_COST_PER_PATIENT_VISIT = 2.50
    SATISFACTION_AMENITIES_BONUS = 10

    AI_ENTERTAINMENT_ENABLED = False
    AI_ENTERTAINMENT_MONTHLY_COST = 5000.00
    SATISFACTION_ENTERTAINMENT_BONUS = 15


class Patient:
    def __init__(self, sim_time):
        self.id = str(uuid.uuid4())
        self.arrival_time = sim_time
        self.acuity = random.choices(
            list(Config.PATIENT_ACUITY.keys()),
            list(Config.PATIENT_ACUITY.values())
        )[0]
        self.events = []
        self.current_unit = 'ED'
        self.status = 'ARRIVED'
        self.needs_imaging = False
        self.imaging_type = None
        self.imaging_start_time = None
        self.imaging_result_time = None
        self.needs_lab = False
        self.lab_start_time = None
        self.lab_result_time = None
        self.discharge_order_time = None
        self.actual_discharge_time = None
        self.assigned_staff_id = None
        self.boarding_start_time = None
        self.imaging_order_unit_id = None
        self.discharge_requested = False
        self.ed_disposition_time = None
        self.transport_request_time = None
        self.transport_assigned_time = None
        self.transport_type = None

    def add_event(self, time, type, unit_id=None):
        self.events.append({'time': time, 'type': type, 'unit_id': unit_id})

    def __lt__(self, other):
        return self.arrival_time < other.arrival_time

    def __le__(self, other):
        return self.arrival_time <= other.arrival_time

    def __gt__(self, other):
        return self.arrival_time > other.arrival_time

    def __ge__(self, other):
        return self.arrival_time >= other.arrival_time

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Patient {self.id[:4]} (Acuity: {self.acuity}, Status: {self.status})"

class Staff:
    def __init__(self, staff_type, id=None):
        self.id = id if id else str(uuid.uuid4())
        self.type = staff_type
        self.busy_until = 0
        self.last_assignment_start_time = None
        self.current_assignment_details = None
        self.last_assigned_unit = None
        self.total_normal_cost = 0
        self.total_overtime_cost = 0

    def assign(self, sim_time, duration, assignment_details, unit_name=None):
        self.accrue_cost_for_completed_task(sim_time)
        self.busy_until = sim_time + duration
        self.last_assignment_start_time = sim_time
        self.current_assignment_details = assignment_details
        self.last_assigned_unit = unit_name

    def is_free(self, sim_time):
        return sim_time >= self.busy_until

    def accrue_cost_for_completed_task(self, current_sim_time):
        if self.last_assignment_start_time is not None and current_sim_time >= self.busy_until:
            duration_worked = self.busy_until - self.last_assignment_start_time
            if duration_worked > 0:
                if self.type == 'VOLUNTEER_TRANSPORT':
                    cost_per_minute = Config.VOLUNTEER_COST
                else:
                    cost_per_minute = getattr(Config, f'{self.type.upper()}_COST')
                
                assignment_cost = cost_per_minute * duration_worked
                overtime_fraction = 0.2 
                self.total_overtime_cost += assignment_cost * overtime_fraction * Config.OVERTIME_MULTIPLIER
                self.total_normal_cost += assignment_cost * (1 - overtime_fraction)
            
            self.last_assignment_start_time = None
            self.current_assignment_details = None
            self.last_assigned_unit = None

    def accrue_remaining_cost(self, final_sim_time):
        if self.last_assignment_start_time is not None:
            duration_worked = min(final_sim_time, self.busy_until) - self.last_assignment_start_time
            if duration_worked > 0:
                if self.type == 'VOLUNTEER_TRANSPORT':
                    cost_per_minute = Config.VOLUNTEER_COST
                else:
                    cost_per_minute = getattr(Config, f'{self.type.upper()}_COST')

                assignment_cost = cost_per_minute * duration_worked
                overtime_fraction = 0.2
                self.total_overtime_cost += assignment_cost * overtime_fraction * Config.OVERTIME_MULTIPLIER
                self.total_normal_cost += assignment_cost * (1 - overtime_fraction)
            self.last_assignment_start_time = None

    def __repr__(self):
        return f"{self.type} Staff {self.id[:4]}"

class Unit:
    def __init__(self, name, capacity, staff_config):
        self.name = name
        self.capacity = capacity
        self.patients_in_unit = {}
        self.queue = []
        self.staff_config = staff_config
        self.staff_assigned = {staff_type: [] for staff_type in staff_config}

    def admit_patient(self, patient, sim_time):
        if len(self.patients_in_unit) < self.capacity:
            self.patients_in_unit[patient.id] = patient
            if patient in self.queue:
                self.queue.remove(patient)
                heapq.heapify(self.queue)
            patient.current_unit = self.name
            patient.add_event(sim_time, f'ADMITTED_TO_{self.name}', self.name)
            return True
        return False

    def add_patient_to_queue(self, patient, sim_time):
        if patient not in self.queue:
            heapq.heappush(self.queue, patient)
            patient.add_event(sim_time, f'QUEUED_FOR_{self.name}', self.name)

    def discharge_patient(self, patient, sim_time):
        if patient.id in self.patients_in_unit:
            del self.patients_in_unit[patient.id]
            patient.add_event(sim_time, f'DISCHARGED_FROM_{self.name}', self.name)
            return True
        return False

    def __repr__(self):
        return f"{self.name} (Capacity: {self.capacity}, Patients: {len(self.patients_in_unit)}, Staff: {self.staff_config})"

class MetricsTracker:
    def __init__(self):
        self.ed_los_list = []
        self.ed_boarding_times = []
        self.total_ed_boarding_time = 0
        self.cdu_conversion_count = 0
        self.cdu_total_patients = 0
        self.cdu_occupancy_times = []
        self.inpatient_occupancy_times = []
        self.overall_imaging_tat = []
        self.critical_imaging_tat = []
        self.ed_cdu_imaging_tat = []
        self.total_patient_count = 0
        self.patient_satisfaction_scores = []
        self.total_hospital_los_list = []
        self.transfer_times_to_admit = []
        self.ed_wait_times_for_transport = []
        self.pulley_utilization_times = []
        self.volunteer_transport_count = 0
        self.paid_transport_count = 0
        self.pulley_transport_count = 0
        self.total_amenities_cost = 0.0
        self.total_ai_entertainment_cost = 0.0

    def add_ed_los(self, los):
        self.ed_los_list.append(los)

    def add_ed_boarding_time(self, boarding_time):
        self.ed_boarding_times.append(boarding_time)
        self.total_ed_boarding_time += boarding_time

    def add_cdu_conversion(self, converted):
        self.cdu_total_patients += 1
        if converted:
            self.cdu_conversion_count += 1

    def add_cdu_occupancy(self, sim_time, patients_in_cdu):
        if not self.cdu_occupancy_times or self.cdu_occupancy_times[-1][1] != patients_in_cdu:
            self.cdu_occupancy_times.append((sim_time, patients_in_cdu))

    def add_inpatient_occupancy(self, sim_time, patients_in_inpatient):
        if not self.inpatient_occupancy_times or self.inpatient_occupancy_times[-1][1] != patients_in_inpatient:
            self.inpatient_occupancy_times.append((sim_time, patients_in_inpatient))

    def add_pulley_utilization(self, sim_time, current_utilization):
        if not self.pulley_utilization_times or self.pulley_utilization_times[-1][1] != current_utilization:
            self.pulley_utilization_times.append((sim_time, current_utilization))

    def add_overall_imaging_tat(self, tat):
        self.overall_imaging_tat.append(tat)

    def add_critical_imaging_tat(self, tat):
        self.critical_imaging_tat.append(tat)

    def add_ed_cdu_imaging_tat(self, tat):
        self.ed_cdu_imaging_tat.append(tat)

    def add_patient_satisfaction_score(self, score):
        self.patient_satisfaction_scores.append(score)

    def add_total_hospital_los(self, los):
        self.total_hospital_los_list.append(los) 
        
    def add_transfer_time_to_admit(self, transfer_time):
        self.transfer_times_to_admit.append(transfer_time)
    
    def add_ed_wait_time_for_transport(self, wait_time):
        self.ed_wait_times_for_transport.append(wait_time)

    def add_transport_type_count(self, transport_type):
        if transport_type == 'VOLUNTEER':
            self.volunteer_transport_count += 1
        elif transport_type == 'PAID_STAFF':
            self.paid_transport_count += 1
        elif transport_type == 'PULLEY':
            self.pulley_transport_count += 1

    def calculate_weighted_average_occupancy(self, occupancy_times_list, total_sim_time_span):
        weighted_patient_minutes = 0
        if len(occupancy_times_list) > 1:
            for i in range(1, len(occupancy_times_list)):
                time_diff = occupancy_times_list[i][0] - occupancy_times_list[i-1][0]
                weighted_patient_minutes += occupancy_times_list[i - 1][1] * time_diff
            weighted_patient_minutes += occupancy_times_list[-1][1] * (Config.SIM_END_TIME - occupancy_times_list[-1][0])
            return weighted_patient_minutes / total_sim_time_span if total_sim_time_span > 0 else 0
        elif occupancy_times_list:
            return occupancy_times_list[0][1]
        else:
            return 0


    def report(self, config_name="Baseline", all_staff_members=None):
        report_data = {}
        print(f"\n--- Metrics Report for: {config_name} ---")

        avg_ed_los = sum(self.ed_los_list) / len(self.ed_los_list) if self.ed_los_list else 0
        print(f"Avg ED LOS (Arrival to Disposition from ED): {avg_ed_los:.2f} minutes")
        report_data["avg_ed_los"] = avg_ed_los

        avg_ed_boarding_time = self.total_ed_boarding_time / len(self.ed_boarding_times) if self.ed_boarding_times else 0
        print(f"Avg ED Boarding Time (Wait for Bed after Triage): {avg_ed_boarding_time:.2f} minutes")
        report_data["avg_ed_boarding"] = avg_ed_boarding_time

        avg_total_hospital_los = sum(self.total_hospital_los_list) / len(self.total_hospital_los_list) if self.total_hospital_los_list else 0
        print(f"Avg Total Hospital LOS (Arrival to Actual Discharge): {avg_total_hospital_los:.2f} minutes")
        report_data["avg_total_hospital_los"] = avg_total_hospital_los

        cdu_conversion_rate = (self.cdu_conversion_count / self.cdu_total_patients) * 100 if self.cdu_total_patients else 0
        print(f"CDU Conversion Rate (Discharge from CDU): {cdu_conversion_rate:.2f}%")
        report_data["cdu_discharge_rate"] = cdu_conversion_rate

        total_sim_time_span = Config.SIM_END_TIME - Config.SIM_START_TIME
        
        avg_cdu_occupancy = self.calculate_weighted_average_occupancy(self.cdu_occupancy_times, total_sim_time_span)
        print(f"Avg CDU Occupancy: {avg_cdu_occupancy:.2f} patients")
        report_data["cdu_avg_occupancy"] = avg_cdu_occupancy
        report_data["cdu_avg_utilization"] = (avg_cdu_occupancy / Config.CDU_BEDS) * 100 if Config.CDU_BEDS > 0 else 0
        print(f"CDU Average Utilization: {report_data['cdu_avg_utilization']:.2f}%")

        avg_inpatient_occupancy = self.calculate_weighted_average_occupancy(self.inpatient_occupancy_times, total_sim_time_span)
        print(f"Avg Inpatient Occupancy: {avg_inpatient_occupancy:.2f} patients")
        report_data["avg_inpatient_occupancy"] = avg_inpatient_occupancy
        report_data["inpatient_avg_utilization"] = (avg_inpatient_occupancy / Config.INPATIENT_BEDS) * 100 if Config.INPATIENT_BEDS > 0 else 0
        print(f"Inpatient Average Utilization: {report_data['inpatient_avg_utilization']:.2f}%")

        avg_pulley_utilization = self.calculate_weighted_average_occupancy(self.pulley_utilization_times, total_sim_time_span)
        print(f"Avg Pulley System Utilization: {avg_pulley_utilization:.2f} slots")
        report_data["pulley_avg_occupancy"] = avg_pulley_utilization
        report_data["pulley_avg_utilization"] = (avg_pulley_utilization / Config.PULLEY_SYSTEM_CAPACITY) * 100 if Config.PULLEY_SYSTEM_CAPACITY > 0 else 0
        print(f"Pulley System Average Utilization: {report_data['pulley_avg_utilization']:.2f}%")
        
        avg_transfer_time_to_admit = sum(self.transfer_times_to_admit) / len(self.transfer_times_to_admit) if self.transfer_times_to_admit else 0
        print(f"Avg Transfer Time (Decision to Admit to New Unit): {avg_transfer_time_to_admit:.2f} minutes")
        report_data["avg_transfer_time_to_admit"] = avg_transfer_time_to_admit

        avg_ed_wait_time_for_transport = sum(self.ed_wait_times_for_transport) / len(self.ed_wait_times_for_transport) if self.ed_wait_times_for_transport else 0
        print(f"Avg ED Wait Time for Transport (After Bed Ready): {avg_ed_wait_time_for_transport:.2f} minutes")
        report_data["avg_ed_wait_for_transport"] = avg_ed_wait_time_for_transport

        print(f"Total Transports by Paid Staff: {self.paid_transport_count}")
        print(f"Total Transports by Volunteers: {self.volunteer_transport_count}")
        print(f"Total Transports by Pulley System: {self.pulley_transport_count}")
        report_data["total_paid_transports"] = self.paid_transport_count
        report_data["total_volunteer_transports"] = self.volunteer_transport_count
        report_data["total_pulley_transports"] = self.pulley_transport_count


        avg_overall_imaging_tat = sum(self.overall_imaging_tat) / len(self.overall_imaging_tat) if self.overall_imaging_tat else 0
        print(f"Avg Overall Imaging TAT (Order to Report): {avg_overall_imaging_tat:.2f} minutes")
        report_data["avg_overall_imaging_tat"] = avg_overall_imaging_tat

        avg_critical_imaging_tat = sum(self.critical_imaging_tat) / len(self.critical_imaging_tat) if self.critical_imaging_tat else 0
        print(f"Avg Critical Imaging TAT: {avg_critical_imaging_tat:.2f} minutes")
        report_data["avg_critical_imaging_tat"] = avg_critical_imaging_tat

        avg_ed_cdu_imaging_tat = sum(self.ed_cdu_imaging_tat) / len(self.ed_cdu_imaging_tat) if self.ed_cdu_imaging_tat else 0
        print(f"Avg ED/CDU Imaging TAT: {avg_ed_cdu_imaging_tat:.2f} minutes")
        report_data["avg_ed_cdu_imaging_tat"] = avg_ed_cdu_imaging_tat

        if self.patient_satisfaction_scores:
            avg_patient_satisfaction_score = sum(self.patient_satisfaction_scores) / len(self.patient_satisfaction_scores)
            print(f"Average ED Patient Satisfaction Score (1-100, 100=best): {avg_patient_satisfaction_score:.2f}")
            report_data["avg_patient_satisfaction_score"] = avg_patient_satisfaction_score
        else:
            print("Patient Satisfaction: No data")
            report_data["avg_patient_satisfaction_score"] = None

        current_normal_staff_cost = 0.0
        current_overtime_staff_cost = 0.0
        total_staff_cost = 0.0

        if all_staff_members:
            for staff_member in all_staff_members.values():
                current_normal_staff_cost += staff_member.total_normal_cost
                current_overtime_staff_cost += staff_member.total_overtime_cost 
            
            print(f"Total Operational Staff Cost (excluding overtime): ${current_normal_staff_cost:.2f}")
            report_data["total_normal_cost"] = current_normal_staff_cost

            print(f"Total Overtime Cost: ${current_overtime_staff_cost:.2f}")
            report_data["total_overtime_cost"] = current_overtime_staff_cost

            total_staff_cost = current_normal_staff_cost + current_overtime_staff_cost
            print(f"Total Staff Cost: ${total_staff_cost:.2f}")
            report_data["total_staff_cost"] = total_staff_cost

        else:
            print("Staff Costs: No staff data available.")
            report_data["total_normal_cost"] = None 
            report_data["total_overtime_cost"] = None
            report_data["total_staff_cost"] = None

        print(f"Total Amenities Cost: ${self.total_amenities_cost:.2f}")
        report_data["total_amenities_cost"] = self.total_amenities_cost
        print(f"Total AI Entertainment Cost: ${self.total_ai_entertainment_cost:.2f}")
        report_data["total_ai_entertainment_cost"] = self.total_ai_entertainment_cost

        total_hospital_expenses = total_staff_cost + self.total_amenities_cost + self.total_ai_entertainment_cost
        print(f"Total Hospital Operational Expenses: ${total_hospital_expenses:.2f}")
        report_data["total_hospital_expenses"] = total_hospital_expenses


        return report_data

    def reset(self):
        self.ed_los_list = []
        self.ed_boarding_times = []
        self.total_ed_boarding_time = 0
        self.cdu_conversion_count = 0
        self.cdu_total_patients = 0
        self.cdu_occupancy_times = []
        self.inpatient_occupancy_times = []
        self.pulley_utilization_times = []
        self.overall_imaging_tat = []
        self.critical_imaging_tat = []
        self.ed_cdu_imaging_tat = []
        self.total_patient_count = 0
        self.patient_satisfaction_scores = []
        self.total_hospital_los_list = []
        self.transfer_times_to_admit = []
        self.ed_wait_times_for_transport = []
        self.pulley_utilization_times = []
        self.volunteer_transport_count = 0
        self.paid_transport_count = 0
        self.pulley_transport_count = 0
        self.total_amenities_cost = 0.0
        self.total_ai_entertainment_cost = 0.0


class HospitalSimulator:
    def __init__(self, config, enable_cdu=False, enable_ai_imaging=False, enable_ai_staffing=False, 
                 enable_amenities=False, enable_ai_entertainment=False, patient_to_trace=""):
        self.config = config
        self.sim_time = config.SIM_START_TIME
        self.total_sim_minutes = config.SIM_END_TIME

        self.patients = {}
        self.event_queue = []

        self.units = {}
        self._initialize_units(enable_cdu)

        self.all_staff = {}
        self._initialize_staff()
        self.metrics = MetricsTracker()

        self.enable_cdu = enable_cdu
        self.enable_ai_imaging = enable_ai_imaging
        self.enable_ai_staffing = enable_ai_staffing
        self.enable_amenities = enable_amenities
        self.enable_ai_entertainment = enable_ai_entertainment

        self.ai_staffing_next_adjustment_time = config.AI_STAFFING_ADJUSTMENT_INTERVAL_MINUTES
        
        self.pulley_in_use = 0

        self.patient_to_trace = patient_to_trace
        self.patient_to_trace_events = defaultdict(list)


    def _initialize_units(self, enable_cdu):
        for unit_name, capacity in self.config.UNIT_CAPACITY.items():
            if unit_name == 'CDU':
                if enable_cdu:
                    self.units[unit_name] = Unit(unit_name, self.config.CDU_BEDS, self.config.STAFF_PER_UNIT.get(unit_name, {}))
                else:
                    self.units[unit_name] = Unit(unit_name, 0, self.config.STAFF_PER_UNIT.get(unit_name, {}))
            else:
                self.units[unit_name] = Unit(unit_name, capacity, self.config.STAFF_PER_UNIT.get(unit_name, {}))

    def _initialize_staff(self):
        for unit_name, staff_config in self.config.STAFF_PER_UNIT.items():
            for staff_type, count in staff_config.items():
                for _ in range(count):
                    staff = Staff(staff_type)
                    self.all_staff[staff.id] = staff
                    self.units[unit_name].staff_assigned[staff_type].append(staff)
        
        for _ in range(self.config.TRANSPORT_STAFF):
            staff = Staff('TRANSPORT')
            self.all_staff[staff.id] = staff
        
        for _ in range(self.config.VOLUNTEER_TRANSPORT_STAFF):
            staff = Staff('VOLUNTEER_TRANSPORT')
            self.all_staff[staff.id] = staff


    def _get_free_bed(self, unit_name):
        unit = self.units.get(unit_name)
        if unit and len(unit.patients_in_unit) < unit.capacity:
            return True
        return False

    def _get_patient_satisfaction_score(self, ed_los):
        max_los_for_score = 480 # 8 hours for a baseline 1
        min_los_for_score = 30 # 30 minutes for a perfect score

        # Base score based on LOS
        if ed_los <= min_los_for_score: base_score = 100
        elif ed_los >= max_los_for_score: base_score = 1
        else:
            base_score = 100 - ((ed_los - min_los_for_score) / (max_los_for_score - min_los_for_score)) * 99
        
        # Apply bonuses for amenities and entertainment
        if self.enable_amenities:
            base_score += self.config.SATISFACTION_AMENITIES_BONUS
        if self.enable_ai_entertainment:
            base_score += self.config.SATISFACTION_ENTERTAINMENT_BONUS

        return max(1, min(100, base_score))

    def _adjust_ai_staffing(self, sim_time):
        self.ai_staffing_next_adjustment_time += self.config.AI_STAFFING_ADJUSTMENT_INTERVAL_MINUTES
        if self.ai_staffing_next_adjustment_time < self.total_sim_minutes:
            heapq.heappush(self.event_queue, (self.ai_staffing_next_adjustment_time, 'AI_STAFFING_ADJUSTMENT', None, None))

    def _determine_patient_disposition(self, patient, event_time):
        if patient.ed_disposition_time is None:
            patient.ed_disposition_time = event_time
            ed_los_val = event_time - patient.arrival_time
            self.metrics.add_ed_los(ed_los_val)
            self.metrics.add_patient_satisfaction_score(self._get_patient_satisfaction_score(ed_los_val))
            if patient.id == self.patient_to_trace:
                self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': f"ED Disposition. LOS: {ed_los_val:.2f} min. Satisfaction: {self._get_patient_satisfaction_score(ed_los_val):.2f}"})

        if patient.acuity in ['CRITICAL', 'URGENT_ADMIT']:
            heapq.heappush(self.event_queue, (event_time, 'ADMIT_TO_INPATIENT', patient.id, None))
            patient.status = 'ADMIT_INPATIENT_PENDING'
        elif patient.acuity == 'URGENT_OBS':
            if self.enable_cdu and random.random() < self.config.CDU_CRITERIA_MATCH:
                heapq.heappush(self.event_queue, (event_time, 'ADMIT_TO_CDU', patient.id, None))
                patient.status = 'ADMIT_CDU_PENDING'
            else:
                heapq.heappush(self.event_queue, (event_time, 'ADMIT_TO_INPATIENT', patient.id, None))
                patient.status = 'ADMIT_INPATIENT_PENDING'
        elif patient.acuity == 'NON_URGENT':
            if self.enable_cdu and random.random() < self.config.CDU_CRITERIA_MATCH * 0.5:
                heapq.heappush(self.event_queue, (event_time, 'ADMIT_TO_CDU', patient.id, None))
                patient.status = 'ADMIT_CDU_PENDING'
            else:
                heapq.heappush(self.event_queue, (event_time, 'DISCHARGE_ORDERED', patient.id, None))
                patient.status = 'DISCHARGE_PENDING_ORDER'
        else:
            print(f"WARNING: Patient {patient.id[:4]} has unhandled acuity {patient.acuity} for disposition at {event_time}. Forcing discharge.")
            heapq.heappush(self.event_queue, (event_time, 'DISCHARGE_ORDERED', patient.id, None))
            patient.status = 'DISCHARGE_PENDING_ORDER'

    def _find_and_assign_staff(self, staff_type, preferred_unit_name, sim_time, duration, assignment_details, patient_id=None):
        staff_pool = []
        if preferred_unit_name and preferred_unit_name in self.units and staff_type in self.units[preferred_unit_name].staff_assigned:
            staff_pool.extend(self.units[preferred_unit_name].staff_assigned[staff_type])
        
        all_staff_of_type = [s for s in self.all_staff.values() if s.type == staff_type]
        for s in all_staff_of_type:
            if s not in staff_pool:
                staff_pool.append(s)

        available_staff = [s for s in staff_pool if s.is_free(sim_time)]
        
        if available_staff:
            selected_staff = min(available_staff, key=lambda s: s.busy_until)
            selected_staff.assign(sim_time, duration, assignment_details, preferred_unit_name)
            if patient_id:
                self.patients[patient_id].assigned_staff_id = selected_staff.id
            return selected_staff
        return None

    def _request_transport_resource(self, patient, event_time, destination_unit_name):
        current_minute_of_day = event_time % self.config.SIM_MINUTES_PER_DAY
        is_volunteer_hours = self.config.VOLUNTEER_HOURS_START <= current_minute_of_day < self.config.VOLUNTEER_HOURS_END
        
        paid_transport_staff = [s for s in self.all_staff.values() if s.type == 'TRANSPORT']
        volunteer_transport_staff = [s for s in self.all_staff.values() if s.type == 'VOLUNTEER_TRANSPORT']
        
        available_paid_staff = [s for s in paid_transport_staff if s.is_free(event_time)]
        available_volunteer_staff = [s for s in volunteer_transport_staff if s.is_free(event_time)]

        # --- Attempt 1: Pulley System --- (Highest Priority)
        if patient.current_unit in self.config.PULLEY_ELIGIBLE_UNITS and \
           destination_unit_name in self.config.PULLEY_ELIGIBLE_DESTINATIONS and \
           self.pulley_in_use < self.config.PULLEY_SYSTEM_CAPACITY:
            
            self.pulley_in_use += 1
            duration = random.randint(*self.config.PULLEY_TRANSFER_PROCESS_TIME)
            patient.transport_type = 'PULLEY'
            patient.transport_assigned_time = event_time
            heapq.heappush(self.event_queue, (event_time + duration, 'PULLEY_TRANSPORT_COMPLETE', patient.id, {'duration': duration}))
            if patient.id == self.patient_to_trace:
                self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': f"Pulley Transport STARTED to {destination_unit_name}. Duration: {duration} min."})
            return ('PULLEY', None, duration)

        # --- Attempt 2: Paid Staff for CRITICAL patients ---
        if patient.acuity == 'CRITICAL' and available_paid_staff:
            selected_staff = min(available_paid_staff, key=lambda s: s.busy_until)
            duration = random.randint(*self.config.TRANSFER_PROCESS_TIME)
            selected_staff.assign(event_time, duration, f'Transport Patient {patient.id} to {destination_unit_name}', patient.current_unit)
            patient.assigned_staff_id = selected_staff.id
            patient.transport_assigned_time = event_time
            patient.transport_type = 'PAID_STAFF'
            heapq.heappush(self.event_queue, (event_time + duration, 'STAFF_TRANSPORT_COMPLETE', patient.id, {'duration': duration}))
            if patient.id == self.patient_to_trace:
                self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': f"Paid Staff Transport (CRITICAL) STARTED to {destination_unit_name}. Staff: {selected_staff.id[:4]}, Duration: {duration} min."})
            return ('PAID_STAFF', selected_staff.id, duration)

        # --- Attempt 3: Volunteer Staff for eligible acuities during volunteer hours --- (Prioritized)
        if is_volunteer_hours and patient.acuity in self.config.VOLUNTEER_ACUITY_ELIGIBILITY and available_volunteer_staff:
            selected_staff = min(available_volunteer_staff, key=lambda s: s.busy_until)
            duration = random.randint(*self.config.VOLUNTEER_TRANSFER_PROCESS_TIME)
            selected_staff.assign(event_time, duration, f'Volunteer Transport Patient {patient.id} to {destination_unit_name}', patient.current_unit)
            patient.assigned_staff_id = selected_staff.id
            patient.transport_assigned_time = event_time
            patient.transport_type = 'VOLUNTEER'
            heapq.heappush(self.event_queue, (event_time + duration, 'STAFF_TRANSPORT_COMPLETE', patient.id, {'duration': duration}))
            if patient.id == self.patient_to_trace:
                self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': f"Volunteer Transport STARTED to {destination_unit_name}. Staff: {selected_staff.id[:4]}, Duration: {duration} min."})
            return ('VOLUNTEER', selected_staff.id, duration)

        # --- Attempt 4: Paid Staff for all other cases --- (Lower Priority for non-critical/volunteer-eligible)
        if available_paid_staff:
            # Sort by acuity then by busy_until for a more nuanced prioritization of paid staff
            sorted_paid_staff = sorted(available_paid_staff, key=lambda s: (Config.TRANSPORT_PRIORITY.get(patient.acuity, 5), s.busy_until))
            selected_staff = sorted_paid_staff[0]

            duration = random.randint(*self.config.TRANSFER_PROCESS_TIME)
            selected_staff.assign(event_time, duration, f'Transport Patient {patient.id} to {destination_unit_name}', patient.current_unit)
            patient.assigned_staff_id = selected_staff.id
            patient.transport_assigned_time = event_time
            patient.transport_type = 'PAID_STAFF'
            heapq.heappush(self.event_queue, (event_time + duration, 'STAFF_TRANSPORT_COMPLETE', patient.id, {'duration': duration}))
            if patient.id == self.patient_to_trace:
                self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': f"Paid Staff Transport (General) STARTED to {destination_unit_name}. Staff: {selected_staff.id[:4]}, Duration: {duration} min."})
            return ('PAID_STAFF', selected_staff.id, duration)
        
        # --- Fail: No transport available ---
        return (None, None, None)


    def _process_event(self, event_time, event_type, patient_id, event_data=None):
        self.sim_time = event_time
        patient = self.patients.get(patient_id)

        if patient_id == self.patient_to_trace:
            self.patient_to_trace_events[patient.id].append({'time': event_time, 'type': event_type, 'data': event_data})

        # --- Event Handling Logic ---
        if event_type == 'SCHEDULE_PATIENT_ARRIVAL':
            new_patient_time = self.sim_time + random.expovariate(self.config.PATIENT_ARRIVAL_RATE)
            if new_patient_time < self.total_sim_minutes:
                heapq.heappush(self.event_queue, (new_patient_time, 'PATIENT_ARRIVAL', None, None))
            heapq.heappush(self.event_queue, (self.sim_time + self.config.TICK_INTERVAL_MINUTES, 'SCHEDULE_PATIENT_ARRIVAL', None, None))


        elif event_type == 'PATIENT_ARRIVAL':
            new_patient = Patient(event_time)
            self.patients[new_patient.id] = new_patient
            self.units['ED'].add_patient_to_queue(new_patient, event_time)
            new_patient.add_event(event_time, 'ARRIVED_AT_ED', 'ED')
            
            if self.enable_amenities:
                self.metrics.total_amenities_cost += self.config.AMENITIES_COST_PER_PATIENT_VISIT

            heapq.heappush(self.event_queue, (event_time + random.randint(*self.config.ED_TRIAGE_TIME), 'ED_TRIAGE_COMPLETE', new_patient.id, None))
            new_patient.status = 'TRIAGING'
            
        elif event_type == 'ED_TRIAGE_COMPLETE':
            if patient.status == 'TRIAGING':
                patient.status = 'ED_TRIAGE_COMPLETE'
                patient.add_event(event_time, 'ED_TRIAGE_COMPLETE_EVENT', 'ED')
                heapq.heappush(self.event_queue, (event_time, 'ASSIGN_ED_BED', patient.id, None))

        elif event_type == 'ASSIGN_ED_BED':
            ed_unit = self.units['ED']
            if self._get_free_bed('ED') and patient.id not in ed_unit.patients_in_unit:
                ed_unit.admit_patient(patient, event_time)
                patient.add_event(event_time, 'ED_BED_ASSIGNED', 'ED')
                patient.status = 'ED_IN_BED'

                physician_assessment_duration = random.randint(*self.config.ED_PHYSICIAN_ASSESSMENT_TIME[patient.acuity])
                free_physician = self._find_and_assign_staff('PHYSICIAN', 'ED', event_time, physician_assessment_duration, f'Assess Patient {patient.id}', patient.id)
                if free_physician:
                    heapq.heappush(self.event_queue, (free_physician.busy_until, 'ED_PHYSICIAN_ASSESSMENT_COMPLETE', patient.id, None))
                    patient.status = 'PHYSICIAN_ASSESSMENT'
                else:
                    heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'ED_PHYSICIAN_RETRY', patient.id, None))
                    patient.status = 'ED_WAIT_FOR_PHYSICIAN'
                    patient.add_event(event_time, 'ED_WAIT_FOR_PHYSICIAN', 'ED')
            else:
                if patient.status != 'ED_WAIT_FOR_BED':
                    patient.boarding_start_time = event_time
                    patient.status = 'ED_WAIT_FOR_BED'
                    patient.add_event(event_time, 'ED_WAIT_FOR_BED_QUEUED', 'ED')
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'ASSIGN_ED_BED', patient.id, None))

        elif event_type == 'ED_PHYSICIAN_RETRY':
            if patient.status == 'ED_WAIT_FOR_PHYSICIAN' and patient.current_unit == 'ED':
                physician_assessment_duration = random.randint(*self.config.ED_PHYSICIAN_ASSESSMENT_TIME[patient.acuity])
                free_physician = self._find_and_assign_staff('PHYSICIAN', 'ED', event_time, physician_assessment_duration, f'Assess Patient {patient.id}', patient.id)
                if free_physician:
                    heapq.heappush(self.event_queue, (free_physician.busy_until, 'ED_PHYSICIAN_ASSESSMENT_COMPLETE', patient.id, None))
                    patient.status = 'PHYSICIAN_ASSESSMENT'
                else:
                    heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'ED_PHYSICIAN_RETRY', patient.id, None))

        elif event_type == 'ED_PHYSICIAN_ASSESSMENT_COMPLETE':
            if patient.boarding_start_time:
                self.metrics.add_ed_boarding_time(event_time - patient.boarding_start_time)
                patient.boarding_start_time = None
            patient.add_event(event_time, 'ED_PHYSICIAN_ASSESSMENT_COMPLETE_EVENT', 'ED')

            patient.needs_imaging = (random.random() < 0.3)
            patient.needs_lab = (random.random() < 0.4)

            if patient.needs_imaging:
                patient.imaging_type = random.choice(['CT', 'MRI'])
                patient.imaging_order_unit_id = patient.current_unit
                heapq.heappush(self.event_queue, (event_time, 'IMAGING_ORDERED', patient.id, None))
                patient.status = 'IMAGING_PENDING'
            elif patient.needs_lab:
                patient.imaging_order_unit_id = patient.current_unit
                heapq.heappush(self.event_queue, (event_time, 'LAB_ORDERED', patient.id, None))
                patient.status = 'LAB_PENDING'
            else:
                self._determine_patient_disposition(patient, event_time)

        elif event_type == 'IMAGING_ORDERED':
            patient.add_event(event_time, 'IMAGING_ORDERED_EVENT', patient.current_unit)
            patient.imaging_start_time = event_time
            
            patient.transport_request_time = event_time
            heapq.heappush(self.event_queue, (event_time, 'TRANSFER_TO_IMAGING', patient.id, None))
            patient.status = 'TRANSFER_TO_IMAGING_PENDING'

        elif event_type == 'TRANSFER_TO_IMAGING':
            imaging_unit_name = f'IMAGING_{patient.imaging_type}'
            
            if not self._get_free_bed(imaging_unit_name):
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'TRANSFER_TO_IMAGING', patient.id, None))
                if patient.status != 'ED_WAIT_FOR_IMAGING_MACHINE':
                    patient.status = 'ED_WAIT_FOR_IMAGING_MACHINE'
                    patient.add_event(event_time, 'ED_WAIT_FOR_IMAGING_MACHINE', patient.current_unit)
                return

            transport_result = self._request_transport_resource(patient, event_time, imaging_unit_name)
            transport_type, staff_id, duration = transport_result

            if transport_type:
                if patient.current_unit in self.units and patient.id in self.units[patient.current_unit].patients_in_unit:
                    self.units[patient.current_unit].discharge_patient(patient, event_time)
                
                patient.current_unit = imaging_unit_name
                patient.status = 'IN_TRANSIT_TO_IMAGING'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'TRANSFER_TO_IMAGING', patient.id, None))
                if patient.status != 'ED_WAIT_FOR_TRANSPORT_TO_IMAGING':
                    patient.status = 'ED_WAIT_FOR_TRANSPORT_TO_IMAGING'
                    patient.add_event(event_time, 'ED_WAIT_FOR_TRANSPORT_TO_IMAGING', patient.current_unit)

        elif event_type == 'PULLEY_TRANSPORT_COMPLETE' or event_type == 'STAFF_TRANSPORT_COMPLETE':
            duration_of_transport = event_data['duration'] if event_data and 'duration' in event_data else 0

            patient.add_event(event_time, f'ARRIVED_AT_{patient.current_unit}', patient.current_unit)
            self.metrics.add_transport_type_count(patient.transport_type)
            self.metrics.add_transfer_time_to_admit(duration_of_transport)
            
            if event_type == 'PULLEY_TRANSPORT_COMPLETE':
                self.pulley_in_use -= 1

            if patient.transport_type != 'PULLEY' and patient.transport_request_time is not None and patient.transport_assigned_time is not None:
                self.metrics.add_ed_wait_time_for_transport(patient.transport_assigned_time - patient.transport_request_time)
            
            if patient.status == 'IN_TRANSIT_TO_IMAGING':
                heapq.heappush(self.event_queue, (event_time, 'IMAGING_STARTED', patient.id, None))
            elif patient.status == 'IN_TRANSIT_TO_LAB':
                heapq.heappush(self.event_queue, (event_time, 'LAB_STARTED', patient.id, None))
            elif patient.status == 'IN_TRANSIT_TO_INPATIENT' or patient.status == 'IN_TRANSIT_TO_CDU':
                target_unit_name = patient.current_unit
                target_unit = self.units[target_unit_name]
                target_unit.admit_patient(patient, event_time)
                patient.add_event(event_time, f'ADMITTED_TO_{target_unit_name}', target_unit_name)
                if patient.boarding_start_time and patient.current_unit == 'ED':
                    self.metrics.add_ed_boarding_time(event_time - patient.boarding_start_time)
                    patient.boarding_start_time = None

                if target_unit_name == 'INPATIENT':
                    stay_duration = random.randint(*self.config.INPATIENT_STAY_TIME[patient.acuity])
                    heapq.heappush(self.event_queue, (event_time + stay_duration, 'INPATIENT_PATIENT_CHECK', patient.id, None))
                    heapq.heappush(self.event_queue, (event_time + self.config.INPATIENT_CDU_CHECK_INTERVAL, 'INPATIENT_PATIENT_CHECK', patient.id, None))
                    patient.status = 'INPATIENT_STAY'
                elif target_unit_name == 'CDU':
                    cdu_obs_duration = random.randint(*self.config.CDU_OBSERVATION_TIME)
                    heapq.heappush(self.event_queue, (event_time + cdu_obs_duration, 'CDU_OBSERVATION_COMPLETE', patient.id, None))
                    patient.status = 'CDU_OBSERVATION'


        elif event_type == 'IMAGING_STARTED':
            imaging_unit_name = patient.current_unit
            imaging_duration = random.randint(*self.config.IMAGING_PROCESSING_TIME[patient.imaging_type])
            if self.enable_ai_imaging:
                if patient.acuity == 'CRITICAL':
                    imaging_duration = int(imaging_duration * (1 - self.config.AI_CRITICAL_REDUCTION))
                else:
                    imaging_duration = int(imaging_duration * (1 - self.config.AI_ROUTINE_PRELIM_REDUCTION))

            imaging_tech = self._find_and_assign_staff('TECH', imaging_unit_name, event_time, imaging_duration, f'Perform {patient.imaging_type} for Patient {patient.id}', patient.id)
            if imaging_tech:
                heapq.heappush(self.event_queue, (imaging_tech.busy_until, 'IMAGING_COMPLETE', patient.id, None))
                patient.status = 'IMAGING_PROCESSING'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'IMAGING_STARTED', patient.id, None))
                patient.status = 'IMAGING_WAIT_FOR_TECH'
                patient.add_event(event_time, 'IMAGING_WAIT_FOR_TECH', imaging_unit_name)

        elif event_type == 'IMAGING_COMPLETE':
            imaging_unit_name = patient.current_unit
            self.units[imaging_unit_name].discharge_patient(patient, event_time)
            patient.add_event(event_time, 'IMAGING_COMPLETE_EVENT', imaging_unit_name)
            patient.status = 'IMAGING_REPORT_PENDING'

            report_time_range = self.config.IMAGING_REPORTING_TIME['CRITICAL'] if patient.acuity == 'CRITICAL' else self.config.IMAGING_REPORTING_TIME['ROUTINE']
            report_duration = random.randint(*report_time_range)
            if self.enable_ai_imaging:
                if patient.acuity == 'CRITICAL':
                    report_duration = int(report_duration * (1 - self.config.AI_CRITICAL_REDUCTION))
                else:
                    report_duration = int(report_duration * (1 - self.config.AI_ROUTINE_PRELIM_REDUCTION))

            radiologist = self._find_and_assign_staff('RADIOLOGIST', 'RADIOLOGY', event_time, report_duration, f'Report {patient.id[:4]} for Patient {patient.id}', patient.id)
            if radiologist:
                heapq.heappush(self.event_queue, (radiologist.busy_until, 'IMAGING_REPORT_COMPLETE', patient.id, None))
                patient.status = 'IMAGING_REPORTING'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'IMAGING_REPORT_RETRY', patient.id, None))
                patient.status = 'IMAGING_REPORT_WAIT_FOR_RADIOLOGIST'
                patient.add_event(event_time, 'IMAGING_REPORT_WAIT_FOR_RADIOLOGIST', 'RADIOLOGY')

        elif event_type == 'IMAGING_REPORT_RETRY':
            if patient.status == 'IMAGING_REPORT_WAIT_FOR_RADIOLOGIST':
                report_time_range = self.config.IMAGING_REPORTING_TIME['CRITICAL'] if patient.acuity == 'CRITICAL' else self.config.IMAGING_REPORTING_TIME['ROUTINE']
                report_duration = random.randint(*report_time_range)
                if self.enable_ai_imaging:
                    if patient.acuity == 'CRITICAL':
                        report_duration = int(report_duration * (1 - self.config.AI_CRITICAL_REDUCTION))
                    else:
                        report_duration = int(report_duration * (1 - self.config.AI_ROUTINE_PRELIM_REDUCTION))
                radiologist = self._find_and_assign_staff('RADIOLOGIST', 'RADIOLOGY', event_time, report_duration, f'Report {patient.imaging_type} for Patient {patient.id}', patient.id)
                if radiologist:
                    heapq.heappush(self.event_queue, (radiologist.busy_until, 'IMAGING_REPORT_COMPLETE', patient.id, None))
                    patient.status = 'IMAGING_REPORTING'
                else:
                    heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'IMAGING_REPORT_RETRY', patient.id, None))

        elif event_type == 'IMAGING_REPORT_COMPLETE':
            patient.imaging_result_time = event_time
            patient.add_event(event_time, 'IMAGING_REPORT_COMPLETE_EVENT', patient.imaging_order_unit_id)

            tat = patient.imaging_result_time - patient.imaging_start_time
            self.metrics.add_overall_imaging_tat(tat)
            if patient.acuity == 'CRITICAL':
                self.metrics.add_critical_imaging_tat(tat)
            if patient.imaging_order_unit_id in ['ED', 'CDU']:
                self.metrics.add_ed_cdu_imaging_tat(tat)

            patient.needs_imaging = False

            patient.current_unit = patient.imaging_order_unit_id
            heapq.heappush(self.event_queue, (event_time, 'RE_EVALUATE_AFTER_DIAGNOSTICS', patient.id, None))
            patient.status = 'DIAGNOSTICS_COMPLETE'

        elif event_type == 'LAB_ORDERED':
            patient.add_event(event_time, 'LAB_ORDERED_EVENT', patient.current_unit)
            patient.lab_start_time = event_time
            
            patient.transport_request_time = event_time
            heapq.heappush(self.event_queue, (event_time, 'TRANSFER_TO_LAB', patient.id, None))
            patient.status = 'TRANSFER_TO_LAB_PENDING'

        elif event_type == 'TRANSFER_TO_LAB':
            lab_unit_name = 'LAB'
            
            if not self._get_free_bed(lab_unit_name):
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'TRANSFER_TO_LAB', patient.id, None))
                if patient.status != 'ED_WAIT_FOR_LAB_CAPACITY':
                    patient.status = 'ED_WAIT_FOR_LAB_CAPACITY'
                    patient.add_event(event_time, 'ED_WAIT_FOR_LAB_CAPACITY', patient.current_unit)
                return

            transport_result = self._request_transport_resource(patient, event_time, lab_unit_name)
            transport_type, staff_id, duration = transport_result

            if transport_type:
                if patient.current_unit in self.units and patient.id in self.units[patient.current_unit].patients_in_unit:
                    self.units[patient.current_unit].discharge_patient(patient, event_time)
                
                patient.current_unit = lab_unit_name
                patient.status = 'IN_TRANSIT_TO_LAB'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'TRANSFER_TO_LAB', patient.id, None))
                if patient.status != 'ED_WAIT_FOR_TRANSPORT_TO_LAB':
                    patient.status = 'ED_WAIT_FOR_TRANSPORT_TO_LAB'
                    patient.add_event(event_time, 'ED_WAIT_FOR_TRANSPORT_TO_LAB', patient.current_unit)

        elif event_type == 'LAB_STARTED':
            lab_unit_name = patient.current_unit
            lab_duration = random.randint(*self.config.LAB_PROCESSING_TIME)
            lab_tech = self._find_and_assign_staff('TECH', 'LAB', event_time, lab_duration, f'Perform Lab for Patient {patient.id}', patient.id)
            if lab_tech:
                self.units['LAB'].admit_patient(patient, event_time)
                heapq.heappush(self.event_queue, (lab_tech.busy_until, 'LAB_COMPLETE', patient.id, None))
                patient.status = 'LAB_PROCESSING'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'LAB_STARTED', patient.id, None))
                patient.status = 'LAB_WAIT_FOR_TECH'
                patient.add_event(event_time, 'LAB_WAIT_FOR_TECH', 'LAB')

        elif event_type == 'LAB_COMPLETE':
            self.units['LAB'].discharge_patient(patient, event_time)
            patient.lab_result_time = event_time
            patient.add_event(event_time, 'LAB_COMPLETE_EVENT', 'LAB')
            patient.needs_lab = False

            patient.current_unit = patient.imaging_order_unit_id
            heapq.heappush(self.event_queue, (event_time, 'RE_EVALUATE_AFTER_DIAGNOSTICS', patient.id, None))
            patient.status = 'DIAGNOSTICS_COMPLETE'

        elif event_type == 'RE_EVALUATE_AFTER_DIAGNOSTICS':
            if patient.needs_imaging:
                heapq.heappush(self.event_queue, (event_time, 'IMAGING_ORDERED', patient.id, None))
                patient.status = 'IMAGING_PENDING'
            elif patient.needs_lab:
                heapq.heappush(self.event_queue, (event_time, 'LAB_ORDERED', patient.id, None))
                patient.status = 'LAB_PENDING'
            else:
                self._determine_patient_disposition(patient, event_time)

        elif event_type == 'ADMIT_TO_INPATIENT' or event_type == 'ADMIT_TO_CDU':
            target_unit_name = 'INPATIENT' if event_type == 'ADMIT_TO_INPATIENT' else 'CDU'
            target_unit = self.units[target_unit_name]

            if not self._get_free_bed(target_unit_name):
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, event_type, patient.id, None))
                if patient.current_unit == 'ED' and patient.status != 'ED_BOARDING':
                    patient.boarding_start_time = event_time
                    patient.status = 'ED_BOARDING'
                    patient.add_event(event_time, 'ED_BOARDING', 'ED')
                return

            patient.transport_request_time = event_time
            transport_result = self._request_transport_resource(patient, event_time, target_unit_name)
            transport_type, staff_id, duration = transport_result
            
            if transport_type:
                if patient.current_unit in self.units and patient.id in self.units[patient.current_unit].patients_in_unit:
                    self.units[patient.current_unit].discharge_patient(patient, event_time)
                
                patient.current_unit = target_unit_name
                patient.status = f'IN_TRANSIT_TO_{target_unit_name.upper()}'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, event_type, patient.id, None))
                if patient.current_unit == 'ED' and patient.status != 'ED_WAIT_FOR_TRANSPORT':
                    patient.status = 'ED_WAIT_FOR_TRANSPORT'
                    patient.add_event(event_time, 'ED_WAIT_FOR_TRANSPORT', 'ED')

        elif event_type == 'CDU_OBSERVATION_COMPLETE':
            if patient and patient.current_unit == 'CDU':
                patient.add_event(event_time, 'CDU_OBSERVATION_COMPLETE_EVENT', 'CDU')
                
                discharge_probability = random.random()

                if discharge_probability < 0.8:
                    self.metrics.add_cdu_conversion(True)
                    heapq.heappush(self.event_queue, (event_time, 'DISCHARGE_ORDERED', patient.id, None))
                    patient.status = 'CDU_DISCHARGE_PENDING'
                else:
                    self.metrics.add_cdu_conversion(False)
                    heapq.heappush(self.event_queue, (event_time, 'ADMIT_TO_INPATIENT', patient.id, None))
                    patient.status = 'CDU_TO_INPATIENT'
            else:
                pass

        elif event_type == 'INPATIENT_PATIENT_CHECK':
            if patient and patient.current_unit == 'INPATIENT' and patient.status == 'INPATIENT_STAY' and not patient.discharge_requested:
                admit_events = [e for e in patient.events if e['type'].startswith('ADMITTED_TO_') and e['unit_id'] == 'INPATIENT']
                if admit_events:
                    admit_event_time = admit_events[0]['time']
                    current_stay_duration = event_time - admit_event_time
                    
                    min_stay_time, max_stay_time = self.config.INPATIENT_STAY_TIME.get(patient.acuity, (1*24*60, 2*24*60))

                    if current_stay_duration >= min_stay_time:
                        if random.random() < 0.85:
                            heapq.heappush(self.event_queue, (event_time, 'DISCHARGE_ORDERED', patient.id, None))
                            patient.discharge_requested = True
                            patient.status = 'DISCHARGE_PENDING_ORDER'
                    
                    if not patient.discharge_requested:
                        heapq.heappush(self.event_queue, (event_time + self.config.INPATIENT_CDU_CHECK_INTERVAL, 'INPATIENT_PATIENT_CHECK', patient.id, None))
            else:
                pass

        elif event_type == 'DISCHARGE_ORDERED':
            if not patient.discharge_order_time:
                patient.discharge_order_time = event_time
                patient.add_event(event_time, 'DISCHARGE_ORDERED_EVENT', patient.current_unit)
                patient.status = 'DISCHARGE_PROCESS'

            discharge_duration = random.randint(*self.config.DISCHARGE_PROCESS_TIME)
            if self.enable_ai_staffing:
                discharge_duration = int(discharge_duration * (1 - self.config.AI_DISCHARGE_REDUCTION))
            
            discharge_nurse = self._find_and_assign_staff('NURSE', patient.current_unit, event_time, discharge_duration, f'Discharge Patient {patient.id}', patient.id)
            if discharge_nurse:
                heapq.heappush(self.event_queue, (discharge_nurse.busy_until, 'DISCHARGE_PROCESS_COMPLETE', patient.id, None))
                patient.status = 'DISCHARGE_PROCESSING'
            else:
                heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'DISCHARGE_PROCESS_RETRY', patient.id, None))
                patient.status = 'DISCHARGE_WAIT_FOR_NURSE'
                patient.add_event(event_time, 'DISCHARGE_WAIT_FOR_NURSE', patient.current_unit)

        elif event_type == 'DISCHARGE_PROCESS_RETRY':
            if patient.status == 'DISCHARGE_WAIT_FOR_NURSE':
                discharge_duration = random.randint(*self.config.DISCHARGE_PROCESS_TIME)
                if self.enable_ai_staffing:
                    discharge_duration = int(discharge_duration * (1 - self.config.AI_DISCHARGE_REDUCTION))
                
                discharge_nurse = self._find_and_assign_staff('NURSE', patient.current_unit, event_time, discharge_duration, f'Discharge Patient {patient.id}', patient.id)
                if discharge_nurse:
                    heapq.heappush(self.event_queue, (discharge_nurse.busy_until, 'DISCHARGE_PROCESS_COMPLETE', patient.id, None))
                    patient.status = 'DISCHARGE_PROCESSING'
                else:
                    heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'DISCHARGE_PROCESS_RETRY', patient.id, None))

        elif event_type == 'DISCHARGE_PROCESS_COMPLETE':
            if patient.current_unit in self.units and patient.id in self.units[patient.current_unit].patients_in_unit:
                self.units[patient.current_unit].discharge_patient(patient, event_time)
            
            patient.actual_discharge_time = event_time
            patient.add_event(event_time, 'PATIENT_DISCHARGED_ACTUAL', 'EXIT')
            patient.status = 'DISCHARGED'
            
            self.metrics.add_total_hospital_los(patient.actual_discharge_time - patient.arrival_time)

        elif event_type == 'AI_STAFFING_ADJUSTMENT':
            if self.enable_ai_staffing:
                self._adjust_ai_staffing(event_time)

        elif event_type == 'CDU_OCCUPANCY_METRIC_CHECK':
            if self.enable_cdu:
                self.metrics.add_cdu_occupancy(event_time, len(self.units['CDU'].patients_in_unit))
                heapq.heappush(self.event_queue, (event_time + self.config.INPATIENT_CDU_CHECK_INTERVAL, 'CDU_OCCUPANCY_METRIC_CHECK', None, None))

        elif event_type == 'INPATIENT_OCCUPANCY_METRIC_CHECK':
            self.metrics.add_inpatient_occupancy(event_time, len(self.units['INPATIENT'].patients_in_unit))
            heapq.heappush(self.event_queue, (event_time + self.config.INPATIENT_CDU_CHECK_INTERVAL, 'INPATIENT_OCCUPANCY_METRIC_CHECK', None, None))

        elif event_type == 'PULLEY_UTILIZATION_METRIC_CHECK':
            self.metrics.add_pulley_utilization(event_time, self.pulley_in_use)
            heapq.heappush(self.event_queue, (event_time + self.config.TICK_INTERVAL_MINUTES, 'PULLEY_UTILIZATION_METRIC_CHECK', None, None))

    
    def run(self):
        start_real_time = time.time()
        print(f"Starting simulation for {self.config.SIM_DAYS} days ({self.total_sim_minutes} minutes)...")

        heapq.heappush(self.event_queue, (self.sim_time, 'SCHEDULE_PATIENT_ARRIVAL', None, None))
        if self.enable_cdu:
            heapq.heappush(self.event_queue, (self.sim_time + self.config.TICK_INTERVAL_MINUTES, 'CDU_OCCUPANCY_METRIC_CHECK', None, None)) 
        heapq.heappush(self.event_queue, (self.sim_time + self.config.TICK_INTERVAL_MINUTES, 'INPATIENT_OCCUPANCY_METRIC_CHECK', None, None))
        heapq.heappush(self.event_queue, (self.sim_time + self.config.TICK_INTERVAL_MINUTES, 'PULLEY_UTILIZATION_METRIC_CHECK', None, None))

        while self.event_queue and self.sim_time < self.total_sim_minutes:
            event_time, event_type, patient_id, event_data = heapq.heappop(self.event_queue)

            if event_time > self.total_sim_minutes:
                continue

            self.sim_time = event_time
            self._process_event(event_time, event_type, patient_id, event_data)

        for staff_member in self.all_staff.values():
            staff_member.accrue_remaining_cost(self.total_sim_minutes + 1)

        if self.enable_ai_entertainment:
            sim_duration_days = self.config.SIM_DAYS
            months_simulated = sim_duration_days / 30.0
            self.metrics.total_ai_entertainment_cost = months_simulated * self.config.AI_ENTERTAINMENT_MONTHLY_COST
        
        end_real_time = time.time()
        print(f"Simulation finished in {end_real_time - start_real_time:.2f} seconds.")

    def get_patient_events_for_debugging(self):
        if self.patient_to_trace and self.patient_to_trace in self.patient_to_trace_events:
            print(f"\n--- Event Timeline for Patient {self.patient_to_trace[:4]} ---")
            for event in sorted(self.patient_to_trace_events[self.patient_to_trace], key=lambda x: x['time']):
                print(f"  Time: {event['time']:.2f}, Event: {event['type']}, Data: {event['data']}")
        else:
            print(f"No events traced for patient {self.patient_to_trace[:4] if self.patient_to_trace else '(specify patient_to_trace)'}.")

# Example Usage:
if __name__ == "__main__":
    patient_to_trace_id = "" # Set a patient ID here to trace their events

    # --- BELLEVUE HOSPITAL CENTER ---
    print("\n--- Simulating Bellevue Hospital Center (Baseline) ---")
    class BellevueBaselineConfig(Config):
        # 1M+ annual visits = ~2740 daily visits. For 7 days, ~19180.
        # Current sim generates ~2500 patients in 7 days with 0.40 rate.
        # Need to scale arrival rate: (19180 / 2500) * 0.40 = ~3.06
        PATIENT_ARRIVAL_RATE = 3.06 
        UNIT_CAPACITY = Config.UNIT_CAPACITY.copy()
        UNIT_CAPACITY['ED'] = 180 # Estimated large ED capacity
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy()
        STAFF_PER_UNIT['ED'] = {'NURSE': math.ceil(180/8 * 0.85), 'PHYSICIAN': 10} # 1:8 nurse/aide, 15% shortage = 85% staffing
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': math.ceil(165/4 * 0.85), 'PHYSICIAN': 7} # Assuming similar shortage for inpatient nurses
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 6} # Baseline radiologists
        TRANSPORT_STAFF = 100 # Baseline paid transport staff
        VOLUNTEER_TRANSPORT_STAFF = 0
        PULLEY_SYSTEM_CAPACITY = 0
        DISCHARGE_PROCESS_TIME = (180, 300) # Reflects 2-day average delay
        IMAGING_REPORTING_TIME = {'ROUTINE': (180, 480), 'CRITICAL': (90, 180)} # Reflects potential delays
        
    simulator_bellevue_baseline = HospitalSimulator(BellevueBaselineConfig(), 
                                                  enable_cdu=False, enable_ai_imaging=False, enable_ai_staffing=False,
                                                  enable_amenities=False, enable_ai_entertainment=False,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_bellevue_baseline.run()
    simulator_bellevue_baseline.metrics.report("Bellevue Baseline", simulator_bellevue_baseline.all_staff)
    simulator_bellevue_baseline.get_patient_events_for_debugging()

    print("\n--- Simulating Bellevue Hospital Center (Enhanced) ---")
    class BellevueEnhancedConfig(BellevueBaselineConfig):
        enable_cdu = True
        AI_ENABLED_IMAGING = True
        AI_DISCHARGE_REDUCTION = 0.10
        AMENITIES_ENABLED = True
        AI_ENTERTAINMENT_ENABLED = True
        TRANSPORT_STAFF = 60 # Optimized paid transport
        VOLUNTEER_TRANSPORT_STAFF = 15
        PULLEY_SYSTEM_CAPACITY = 2
        # Apply ZBRAIN optimal staffing and efficiencies
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy() # Start from global optimized defaults
        STAFF_PER_UNIT['ED'] = {'NURSE': 14, 'PHYSICIAN': 8} # ZBRAIN optimized
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': 35, 'PHYSICIAN': 7} # ZBRAIN optimized
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 14} # ZBRAIN optimized
        STAFF_PER_UNIT['IMAGING_CT'] = {'TECH': 8}
        STAFF_PER_UNIT['IMAGING_MRI'] = {'TECH': 6}
        DISCHARGE_PROCESS_TIME = (90, 150) # ZBRAIN optimized
        IMAGING_REPORTING_TIME = Config.IMAGING_REPORTING_TIME.copy() # ZBRAIN optimized
        
    simulator_bellevue_enhanced = HospitalSimulator(BellevueEnhancedConfig(), 
                                                  enable_cdu=True, enable_ai_imaging=True, enable_ai_staffing=True,
                                                  enable_amenities=True, enable_ai_entertainment=True,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_bellevue_enhanced.run()
    simulator_bellevue_enhanced.metrics.report("Bellevue Enhanced", simulator_bellevue_enhanced.all_staff)
    simulator_bellevue_enhanced.get_patient_events_for_debugging()

    # --- JACKSON MEMORIAL HOSPITAL ---
    print("\n--- Simulating Jackson Memorial Hospital (Baseline) ---")
    class JacksonBaselineConfig(Config):
        # 170K annual visits = ~466 daily visits. For 7 days, ~3262.
        # Scale arrival rate: (3262 / 2500) * 0.40 = ~0.52
        PATIENT_ARRIVAL_RATE = 0.52 
        UNIT_CAPACITY = Config.UNIT_CAPACITY.copy()
        UNIT_CAPACITY['ED'] = 60 # Estimated ED capacity
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy()
        STAFF_PER_UNIT['ED'] = {'NURSE': math.ceil(60/4 * 0.7), 'PHYSICIAN': 6} # 1:4 nurse/patient, 30% shortage = 70% staffing
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': math.ceil(165/4 * 0.8), 'PHYSICIAN': 6} # Assuming 20% shortage for inpatient nurses
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 5} # Baseline radiologists
        TRANSPORT_STAFF = 100 # Baseline paid transport staff
        VOLUNTEER_TRANSPORT_STAFF = 0
        PULLEY_SYSTEM_CAPACITY = 0
        DISCHARGE_PROCESS_TIME = (120, 240) # Reflects boarding delays
        IMAGING_REPORTING_TIME = {'ROUTINE': (150, 400), 'CRITICAL': (75, 150)} # Reflects potential delays
        
    simulator_jackson_baseline = HospitalSimulator(JacksonBaselineConfig(), 
                                                  enable_cdu=False, enable_ai_imaging=False, enable_ai_staffing=False,
                                                  enable_amenities=False, enable_ai_entertainment=False,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_jackson_baseline.run()
    simulator_jackson_baseline.metrics.report("Jackson Baseline", simulator_jackson_baseline.all_staff)
    simulator_jackson_baseline.get_patient_events_for_debugging()

    print("\n--- Simulating Jackson Memorial Hospital (Enhanced) ---")
    class JacksonEnhancedConfig(JacksonBaselineConfig):
        enable_cdu = True
        AI_ENABLED_IMAGING = True
        AI_DISCHARGE_REDUCTION = 0.10
        AMENITIES_ENABLED = True
        AI_ENTERTAINMENT_ENABLED = True
        TRANSPORT_STAFF = 60 # Optimized paid transport
        VOLUNTEER_TRANSPORT_STAFF = 15
        PULLEY_SYSTEM_CAPACITY = 2
        # Apply ZBRAIN optimal staffing and efficiencies
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy() # Start from global optimized defaults
        STAFF_PER_UNIT['ED'] = {'NURSE': 14, 'PHYSICIAN': 8} # ZBRAIN optimized
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': 35, 'PHYSICIAN': 7} # ZBRAIN optimized
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 14} # ZBRAIN optimized
        STAFF_PER_UNIT['IMAGING_CT'] = {'TECH': 8}
        STAFF_PER_UNIT['IMAGING_MRI'] = {'TECH': 6}
        DISCHARGE_PROCESS_TIME = (90, 150) # ZBRAIN optimized
        IMAGING_REPORTING_TIME = Config.IMAGING_REPORTING_TIME.copy() # ZBRAIN optimized

    simulator_jackson_enhanced = HospitalSimulator(JacksonEnhancedConfig(), 
                                                  enable_cdu=True, enable_ai_imaging=True, enable_ai_staffing=True,
                                                  enable_amenities=True, enable_ai_entertainment=True,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_jackson_enhanced.run()
    simulator_jackson_enhanced.metrics.report("Jackson Enhanced", simulator_jackson_enhanced.all_staff)
    simulator_jackson_enhanced.get_patient_events_for_debugging()

    # --- CEDARS-SINAI MEDICAL CENTER ---
    print("\n--- Simulating Cedars-Sinai Medical Center (Baseline) ---")
    class CedarsSinaiBaselineConfig(Config):
        # 80K annual ED visits = ~219 daily visits. For 7 days, ~1533.
        # Scale arrival rate: (1533 / 2500) * 0.40 = ~0.24
        PATIENT_ARRIVAL_RATE = 0.24 
        UNIT_CAPACITY = Config.UNIT_CAPACITY.copy()
        UNIT_CAPACITY['ED'] = 70 # Estimated ED capacity
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy()
        STAFF_PER_UNIT['ED'] = {'NURSE': math.ceil(70/4 * 0.85), 'PHYSICIAN': 8} # 1:4 nurse/patient, 15% shortage = 85% staffing
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': math.ceil(165/4 * 0.85), 'PHYSICIAN': 7} # Assuming 15% shortage for inpatient nurses
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 7} # Baseline radiologists
        TRANSPORT_STAFF = 100 # Baseline paid transport staff
        VOLUNTEER_TRANSPORT_STAFF = 0
        PULLEY_SYSTEM_CAPACITY = 0
        DISCHARGE_PROCESS_TIME = (100, 200) # Reflects 1.5-day inflation from readmissions
        IMAGING_REPORTING_TIME = {'ROUTINE': (150, 400), 'CRITICAL': (75, 150)} # Reflects potential delays
        
    simulator_cedars_baseline = HospitalSimulator(CedarsSinaiBaselineConfig(), 
                                                  enable_cdu=False, enable_ai_imaging=False, enable_ai_staffing=False,
                                                  enable_amenities=False, enable_ai_entertainment=False,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_cedars_baseline.run()
    simulator_cedars_baseline.metrics.report("Cedars-Sinai Baseline", simulator_cedars_baseline.all_staff)
    simulator_cedars_baseline.get_patient_events_for_debugging()

    print("\n--- Simulating Cedars-Sinai Medical Center (Enhanced) ---")
    class CedarsSinaiEnhancedConfig(CedarsSinaiBaselineConfig):
        enable_cdu = True
        AI_ENABLED_IMAGING = True
        AI_DISCHARGE_REDUCTION = 0.10
        AMENITIES_ENABLED = True
        AI_ENTERTAINMENT_ENABLED = True
        TRANSPORT_STAFF = 60 # Optimized paid transport
        VOLUNTEER_TRANSPORT_STAFF = 15
        PULLEY_SYSTEM_CAPACITY = 2
        # Apply ZBRAIN optimal staffing and efficiencies
        STAFF_PER_UNIT = Config.STAFF_PER_UNIT.copy() # Start from global optimized defaults
        STAFF_PER_UNIT['ED'] = {'NURSE': 14, 'PHYSICIAN': 8} # ZBRAIN optimized
        STAFF_PER_UNIT['INPATIENT'] = {'NURSE': 35, 'PHYSICIAN': 7} # ZBRAIN optimized
        STAFF_PER_UNIT['RADIOLOGY'] = {'RADIOLOGIST': 14} # ZBRAIN optimized
        STAFF_PER_UNIT['IMAGING_CT'] = {'TECH': 8}
        STAFF_PER_UNIT['IMAGING_MRI'] = {'TECH': 6}
        DISCHARGE_PROCESS_TIME = (90, 150) # ZBRAIN optimized
        IMAGING_REPORTING_TIME = Config.IMAGING_REPORTING_TIME.copy() # ZBRAIN optimized
        
    simulator_cedars_enhanced = HospitalSimulator(CedarsSinaiEnhancedConfig(), 
                                                  enable_cdu=True, enable_ai_imaging=True, enable_ai_staffing=True,
                                                  enable_amenities=True, enable_ai_entertainment=True,
                                                  patient_to_trace=patient_to_trace_id)
    simulator_cedars_enhanced.run()
    simulator_cedars_enhanced.metrics.report("Cedars-Sinai Enhanced", simulator_cedars_enhanced.all_staff)
    simulator_cedars_enhanced.get_patient_events_for_debugging()