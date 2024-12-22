#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QGridLayout, QTableWidget, QHeaderView,
                             QTableWidgetItem, QFileDialog, QDateEdit, QScrollArea)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont
import datetime
import random
import csv

# Константы
START_OF_SHIFT = datetime.time(6, 0)
END_OF_SHIFT = datetime.time(3, 0)
MORNING_PEAK_START = datetime.time(7, 0)
MORNING_PEAK_END = datetime.time(9, 0)
EVENING_PEAK_START = datetime.time(17, 0)
EVENING_PEAK_END = datetime.time(19, 0)
MIN_CHANGE_TIME = 10
MAX_CHANGE_TIME = 15
TYPE_A_HOURS = 8
TYPE_A_LUNCH = 60
TYPE_B_HOURS = 12
TYPE_B_SHORT_BREAK = 15
TYPE_B_BREAK_INTERVAL = 120
TYPE_B_LONG_BREAK = 40
MIN_ROUTE_TIME = 65
MAX_ROUTE_TIME = 75
TOTAL_PASSENGERS = 1000
PEAK_PERCENTAGE = 0.7

# Параметры генетического алгоритма
POPULATION_SIZE_GA = 100
GENERATIONS_GA = 250
MUTATION_RATE_GA = 0.1

# Дни недели
REGULAR_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
OFF_DAYS = ["Saturday", "Sunday"]

# Структуры данных
class Itinerary:
    def __init__(self, start_time, duration, operator_id):
        self.start = start_time
        self.end = start_time + datetime.timedelta(minutes=duration)
        self.driver = operator_id

    def __repr__(self):
         return f"Itinerary(start={self.start.strftime('%H:%M')}, end={self.end.strftime('%H:%M')}, driver={self.driver})"

class BusOperator:
    def __init__(self, operator_type, operator_id):
        self.type = operator_type
        self.schedule = []
        self.total_time = datetime.timedelta()
        self.last_rest = datetime.datetime.combine(datetime.date.min, START_OF_SHIFT)
        self.id = operator_id

    def __repr__(self):
        return f"BusOperator(id={self.id}, type={self.type}, schedule={len(self.schedule)} shifts, worktime = {self.total_time})"

class ScheduleBoard:
    def __init__(self):
        self.itineraries = []
        self.operators = []

    def add_itinerary(self, itinerary):
        self.itineraries.append(itinerary)

    def add_operator(self, operator):
        self.operators.append(operator)

    def calculate_statistics(self):
        peak_itineraries = 0
        for itinerary in self.itineraries:
            if (
                (itinerary.start.time() >= MORNING_PEAK_START and itinerary.start.time() < MORNING_PEAK_END) or
                (itinerary.start.time() >= EVENING_PEAK_START and itinerary.start.time() < EVENING_PEAK_END)
                ):
                peak_itineraries += 1
        unique_drivers = len(self.operators)
        total_itineraries = len(self.itineraries)
        return total_itineraries, peak_itineraries, unique_drivers

# Проверка на час пик
def is_peak_time(time):
    return (time >= MORNING_PEAK_START and time < MORNING_PEAK_END) or (time >= EVENING_PEAK_START and time < EVENING_PEAK_END)

# Проверка выходного дня
def is_off_day(date):
    return date.strftime('%A') in OFF_DAYS

# Прямой алгоритм создания расписания
def create_linear_schedule(bus_count, type_a_drivers, type_b_drivers, current_date):
    schedule = ScheduleBoard()
    operators_a = []
    operators_b = []
    current_time = datetime.datetime.combine(current_date, START_OF_SHIFT)

    for i in range(type_a_drivers):
        operators_a.append(BusOperator('A', f'A{i+1}'))

    for i in range(type_b_drivers):
        operators_b.append(BusOperator('B', f'B{i+1}'))

    available_operators_a = list(operators_a)
    available_operators_b = list(operators_b)
   
    while current_time < datetime.datetime.combine(current_date, datetime.time(23, 59)):
        route_duration = random.randint(MIN_ROUTE_TIME, MAX_ROUTE_TIME)
        if is_peak_time(current_time.time()) and not is_off_day(current_date):
            for _ in range(int(bus_count*PEAK_PERCENTAGE)):
                if not available_operators_a and not available_operators_b:
                     break # Если нет доступных водителей, выходим из цикла
                 # Пытаемся найти свободного водителя типа А
                operator = None
                for i, op in enumerate(available_operators_a):
                    last_itinerary_end = datetime.datetime.combine(current_date, START_OF_SHIFT)
                    if op.schedule:
                        for start, end, _ in reversed(op.schedule):
                             last_itinerary_end = end
                             break
                    if current_time >= last_itinerary_end and op.total_time + datetime.timedelta(minutes=route_duration) <= datetime.timedelta(hours=TYPE_A_HOURS):
                         operator = op
                         break # Нашли подходящего водителя
                if operator:
                    itinerary = Itinerary(current_time, route_duration, operator.id)
                    schedule.add_itinerary(itinerary)
                    operator.schedule.append((itinerary.start, itinerary.end, 'route'))
                    operator.total_time += datetime.timedelta(minutes=route_duration)
                    if operator.total_time >= datetime.timedelta(hours=TYPE_A_HOURS):
                         try:
                           available_operators_a.remove(operator)
                         except ValueError:
                            pass # Пропускаем ошибку
                     
                    continue

                 # Если не нашли свободного водителя типа А, то пробуем найти водителя типа B
                for i, operator in enumerate(available_operators_b):
                    if operator.total_time >= datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL) and operator.last_rest <= current_time - datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL):
                           break_start_time = current_time
                           break_end_time = current_time + datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                           operator.schedule.append((break_start_time, break_end_time, 'break'))
                           operator.total_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                           operator.last_rest = break_end_time
                           current_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                           break
                if not operator:
                    for i, op in enumerate(available_operators_b):
                       last_itinerary_end = datetime.datetime.combine(current_date, START_OF_SHIFT)
                       if op.schedule:
                           for start, end, _ in reversed(op.schedule):
                               last_itinerary_end = end
                               break
                       if current_time >= last_itinerary_end:
                          operator = op
                          break
                if operator:
                    itinerary = Itinerary(current_time, route_duration, operator.id)
                    schedule.add_itinerary(itinerary)
                    operator.schedule.append((itinerary.start, itinerary.end, 'route'))
                    operator.total_time += datetime.timedelta(minutes=route_duration)
                    if operator.total_time >= datetime.timedelta(hours=TYPE_B_HOURS):
                        try:
                           available_operators_b.remove(operator)
                        except ValueError:
                            pass
        else:
            passenger_percent = 1 - PEAK_PERCENTAGE if not is_off_day(current_date) else 1
            for _ in range(int(bus_count * passenger_percent)):
                if not available_operators_a and not available_operators_b:
                    break
                 # Пытаемся найти свободного водителя типа А
                operator = None
                for i, op in enumerate(available_operators_a):
                    last_itinerary_end = datetime.datetime.combine(current_date, START_OF_SHIFT)
                    if op.schedule:
                        for start, end, _ in reversed(op.schedule):
                            last_itinerary_end = end
                            break
                    if current_time >= last_itinerary_end and op.total_time + datetime.timedelta(minutes=route_duration) <= datetime.timedelta(hours=TYPE_A_HOURS):
                        operator = op
                        break
                if operator:
                    itinerary = Itinerary(current_time, route_duration, operator.id)
                    schedule.add_itinerary(itinerary)
                    operator.schedule.append((itinerary.start, itinerary.end, 'route'))
                    operator.total_time += datetime.timedelta(minutes=route_duration)
                    if operator.total_time >= datetime.timedelta(hours=TYPE_A_HOURS):
                        try:
                            available_operators_a.remove(operator)
                        except ValueError:
                            pass # Пропускаем ошибку
                        continue # Переходим к следующему итератору
                # Если не нашли свободного водителя типа А, то пробуем найти водителя типа B
                for i, operator in enumerate(available_operators_b):
                    if operator.total_time >= datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL) and operator.last_rest <= current_time - datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL):
                            break_start_time = current_time
                            break_end_time = current_time + datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            operator.schedule.append((break_start_time, break_end_time, 'break'))
                            operator.total_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            operator.last_rest = break_end_time
                            current_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            break
                if not operator:
                    for i, op in enumerate(available_operators_b):
                        last_itinerary_end = datetime.datetime.combine(current_date, START_OF_SHIFT)
                        if op.schedule:
                            for start, end, _ in reversed(op.schedule):
                                last_itinerary_end = end
                                break
                        if current_time >= last_itinerary_end:
                            operator = op
                            break

                if operator:
                    itinerary = Itinerary(current_time, route_duration, operator.id)
                    schedule.add_itinerary(itinerary)
                    operator.schedule.append((itinerary.start, itinerary.end, 'route'))
                    operator.total_time += datetime.timedelta(minutes=route_duration)
                    if operator.total_time >= datetime.timedelta(hours=TYPE_B_HOURS):
                        try:
                            available_operators_b.remove(operator)
                        except ValueError:
                            pass
        current_time += datetime.timedelta(minutes=route_duration + random.randint(MIN_CHANGE_TIME, MAX_CHANGE_TIME))
    
    schedule.operators.extend(operators_a)
    schedule.operators.extend(operators_b)
    return schedule

# Генерация случайного расписания для генетического алгоритма
def generate_initial_schedule(bus_count, type_a_drivers, type_b_drivers, current_date):
    schedule = ScheduleBoard()
    drivers = []
    for i in range(type_a_drivers):
        drivers.append(BusOperator('A', f'A{i+1}'))
    for i in range(type_b_drivers):
        drivers.append(BusOperator('B', f'B{i+1}'))
    
    current_time = datetime.datetime.combine(current_date, START_OF_SHIFT)
    
    while current_time < datetime.datetime.combine(current_date, datetime.time(23, 59)):
        route_duration = random.randint(MIN_ROUTE_TIME, MAX_ROUTE_TIME)
        if is_peak_time(current_time.time()) and not is_off_day(current_date):
            for _ in range(int(bus_count * PEAK_PERCENTAGE)):
                if drivers:
                    driver = random.choice(drivers)
                    last_itinerary_end = datetime.datetime.combine(current_date,START_OF_SHIFT) 
                    if driver.schedule:
                        for start, end, _ in reversed(driver.schedule):
                            last_itinerary_end = end
                            break
                    if  driver.type == 'A' and current_time >= last_itinerary_end and driver.total_time + datetime.timedelta(minutes=route_duration) <= datetime.timedelta(hours=TYPE_A_HOURS) :
                        itinerary = Itinerary(current_time, route_duration, driver.id)
                        schedule.add_itinerary(itinerary)
                        driver.schedule.append((itinerary.start, itinerary.end, 'route'))
                        driver.total_time += datetime.timedelta(minutes=route_duration)
                    elif driver.type == 'B':
                        
                        if driver.total_time >= datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL) and driver.last_rest <= current_time - datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL):
                            break_start_time = current_time
                            break_end_time = current_time + datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            driver.schedule.append((break_start_time, break_end_time, 'break'))
                            driver.total_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            driver.last_rest = break_end_time
                            current_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            continue
                        else:
                            last_itinerary_end = datetime.datetime.combine(current_date,START_OF_SHIFT)
                            if driver.schedule:
                                for start, end, _ in reversed(driver.schedule):
                                    last_itinerary_end = end
                                    break
                            if current_time >= last_itinerary_end:
                                itinerary = Itinerary(current_time, route_duration, driver.id)
                                schedule.add_itinerary(itinerary)
                                driver.schedule.append((itinerary.start, itinerary.end, 'route'))
                                driver.total_time += datetime.timedelta(minutes=route_duration)
                    else:
                        drivers.remove(driver)
                        continue
                else:
                    break
        else:
            passenger_percent = 1 - PEAK_PERCENTAGE if not is_off_day(current_date) else 1
            for _ in range(int(bus_count * passenger_percent)):
                if drivers:
                    driver = random.choice(drivers)
                    last_itinerary_end = datetime.datetime.combine(current_date,START_OF_SHIFT)
                    if driver.schedule:
                        for start, end, _ in reversed(driver.schedule):
                            last_itinerary_end = end
                            break
                    if driver.type == 'A' and current_time >= last_itinerary_end and driver.total_time + datetime.timedelta(minutes=route_duration) <= datetime.timedelta(hours=TYPE_A_HOURS) :
                        itinerary = Itinerary(current_time, route_duration, driver.id)
                        schedule.add_itinerary(itinerary)
                        driver.schedule.append((itinerary.start, itinerary.end, 'route'))
                        driver.total_time += datetime.timedelta(minutes=route_duration)
                    elif driver.type == 'B':
                        if driver.total_time >= datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL) and driver.last_rest <= current_time - datetime.timedelta(minutes=TYPE_B_BREAK_INTERVAL):
                            break_start_time = current_time
                            break_end_time = current_time + datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            driver.schedule.append((break_start_time, break_end_time, 'break'))
                            driver.total_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            driver.last_rest = break_end_time
                            current_time += datetime.timedelta(minutes=TYPE_B_LONG_BREAK)
                            continue
                        else:
                            last_itinerary_end = datetime.datetime.combine(current_date,START_OF_SHIFT)
                            if driver.schedule:
                                for start, end, _ in reversed(driver.schedule):
                                    last_itinerary_end = end
                                    break
                            if current_time >= last_itinerary_end:
                                itinerary = Itinerary(current_time, route_duration, driver.id)
                                schedule.add_itinerary(itinerary)
                                driver.schedule.append((itinerary.start, itinerary.end, 'route'))
                                driver.total_time += datetime.timedelta(minutes=route_duration)
                    else:
                        drivers.remove(driver)
                        continue
                else:
                     break
        current_time += datetime.timedelta(minutes=route_duration + random.randint(MIN_CHANGE_TIME, MAX_CHANGE_TIME))

    schedule.operators.extend(drivers)
    return schedule

# Функция оценки качества расписания для генетического алгоритма
def assess_schedule(schedule):
    total_itineraries, peak_itineraries, unique_drivers = schedule.calculate_statistics()
    return  total_itineraries - unique_drivers*0.1

# Функция скрещивания расписаний для генетического алгоритма
def combine_schedules(schedule1, schedule2):
    split_point = random.randint(0, min(len(schedule1.itineraries), len(schedule2.itineraries)))
    child_schedule = ScheduleBoard()
    child_schedule.itineraries = schedule1.itineraries[:split_point] + schedule2.itineraries[split_point:]

    split_point = random.randint(0, min(len(schedule1.operators), len(schedule2.operators)))
    child_schedule.operators = schedule1.operators[:split_point] + schedule2.operators[split_point:]
    return child_schedule

# Функция мутации расписания для генетического алгоритма
def alter_schedule(schedule):
    if random.random() < MUTATION_RATE_GA:
        if schedule.itineraries:
            index_route_mutate = random.randint(0, len(schedule.itineraries)-1)
            new_start_time = schedule.itineraries[index_route_mutate].start + datetime.timedelta(minutes=random.randint(-30,30))
        if new_start_time > datetime.datetime.combine(datetime.date.min, START_OF_SHIFT) and new_start_time < datetime.datetime.combine(datetime.date.min, END_OF_SHIFT) + datetime.timedelta(days=1):
            schedule.itineraries[index_route_mutate] = Itinerary(new_start_time, random.randint(MIN_ROUTE_TIME, MAX_ROUTE_TIME), schedule.itineraries[index_route_mutate].driver)
    if schedule.operators:
        index_driver_mutate = random.randint(0, len(schedule.operators) - 1)
        schedule.operators[index_driver_mutate].type = random.choice(['A', 'B'])
    return schedule

# Генетический алгоритм
def genetic_optimizer(bus_count, type_a_drivers, type_b_drivers, current_date):
    population = [generate_initial_schedule(bus_count, type_a_drivers, type_b_drivers, current_date) for _ in range(POPULATION_SIZE_GA)]

    for generation in range(GENERATIONS_GA):
        population.sort(key=assess_schedule, reverse=True)
        parents = population[:POPULATION_SIZE_GA // 2]

        offspring = []
        for i in range(0, len(parents), 2):
            if i+1 < len(parents):
                child1 = combine_schedules(parents[i], parents[i+1])
                child2 = combine_schedules(parents[i+1], parents[i])
                offspring.append(alter_schedule(child1))
                offspring.append(alter_schedule(child2))
            else:
                 offspring.append(alter_schedule(parents[i]))

        population = parents + offspring
        population.sort(key=assess_schedule, reverse=True)
        population = population[:POPULATION_SIZE_GA]

    return population[0]

# Запись расписания в CSV-файл
def export_schedule_to_csv(linear_schedule, optimized_schedule, filename, current_date):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Algorithm', 'Operator ID', 'Schedule'])
        
        for schedule, algorithm_name in [(linear_schedule, "Linear"), (optimized_schedule, "Genetic")]:
          for operator in schedule.operators:
            shifts_text = ""
            for start, end, type in operator.schedule:
              start_datetime = start
              end_datetime = end
              if type == 'route':
                  shifts_text += f"Работа: {start_datetime.strftime('%Y-%m-%d %H:%M')}-{end_datetime.strftime('%Y-%m-%d %H:%M')}, "
              elif type == 'break':
                  shifts_text += f"Перерыв: {start_datetime.strftime('%Y-%m-%d %H:%M')}-{end_datetime.strftime('%Y-%m-%d %H:%M')}, "
            shifts_text = shifts_text.rstrip(", ")
            writer.writerow([algorithm_name, operator.id, shifts_text])

# Запись сравнения результатов в CSV-файл
def export_comparison_to_csv(linear_metrics, optimized_metrics, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Metric', 'Linear Algorithm', 'Genetic Algorithm'])
        writer.writerow(['Total Itineraries', linear_metrics[0], optimized_metrics[0]])
        writer.writerow(['Peak Itineraries', linear_metrics[1], optimized_metrics[1]])
        writer.writerow(['Unique Operators', linear_metrics[2], optimized_metrics[2]])

# Отображение расписания в таблице
def display_schedule_in_table(linear_schedule, optimized_schedule, table, current_date):
    table.clearContents()
    table.setRowCount(0)

    schedule_data = []
    
    for schedule, algorithm_name in [(linear_schedule, "Линейный"), (optimized_schedule, "Генетический")]:
      for driver in schedule.operators:
          if not driver.schedule:  # Check if driver has any schedule
                continue # Skip drivers without routes
          driver_schedules = []
          for start, end, type in driver.schedule:
             driver_schedules.append((start, end, type))
          
          shifts_text = ""
          total_work_time = 0
          total_break_time = 0
          
          for start, end, type in driver_schedules:
            if type == 'route':
              total_work_time += (end - start).total_seconds() / 60
              shifts_text += f"Работа: {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, "
            elif type == 'break':
              total_break_time += (end - start).total_seconds() / 60
              shifts_text += f"Перерыв: {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, "
            
          shifts_text = shifts_text.rstrip(", ")
          
          
          schedule_data.append((algorithm_name, driver.id, shifts_text, f"{int(total_work_time)} мин", f"{int(total_break_time)} мин"))
    
    table.setHorizontalHeaderLabels(["Алгоритм", "Водитель", "Расписание", "Время работы", "Время перерыва"])
    table.setColumnCount(5)

    for row, (algorithm, driver_id, shifts, work_time, break_time) in enumerate(schedule_data):
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(algorithm))
        table.setItem(row, 1, QTableWidgetItem(driver_id))
        table.setItem(row, 2, QTableWidgetItem(shifts))
        table.setItem(row, 3, QTableWidgetItem(work_time))
        table.setItem(row, 4, QTableWidgetItem(break_time))
        
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

# Функция запуска алгоритмов и отображения результатов
def execute_and_present():
    try:
        bus_count = int(bus_entry.text())
        type_a_drivers = int(driver_a_entry.text())
        type_b_drivers = int(driver_b_entry.text())
        selected_date = date_entry.date().toPyDate()
    
        linear_schedule = create_linear_schedule(bus_count, type_a_drivers, type_b_drivers, selected_date)
        optimized_schedule = genetic_optimizer(bus_count, type_a_drivers, type_b_drivers, selected_date)

        linear_metrics = linear_schedule.calculate_statistics()
        optimized_metrics = optimized_schedule.calculate_statistics()

        display_schedule_in_table(linear_schedule, optimized_schedule, schedule_table, selected_date)

        metrics_text.setText(f"Линейный: Поездок={linear_metrics[0]}, В пик={linear_metrics[1]}, Водителей={linear_metrics[2]} "
                                 f"Генетический: Поездок={optimized_metrics[0]}, В пик={optimized_metrics[1]}, Водителей={optimized_metrics[2]}")
        export_comparison_to_csv(linear_metrics, optimized_metrics, 'comparison_results.csv')
    except ValueError as e:
        metrics_text.setText(f"Ошибка: {e}")


# Создание основного окна
app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("Генератор расписания автобусов")
layout = QGridLayout()

# Поля ввода
bus_label = QLabel("Количество автобусов:")
layout.addWidget(bus_label, 0, 0)
bus_entry = QLineEdit("8")
layout.addWidget(bus_entry, 0, 1)

date_label = QLabel("Выберите дату:")
layout.addWidget(date_label, 0, 2)
date_entry = QDateEdit(calendarPopup=True)
date_entry.setDate(QDate.currentDate())
layout.addWidget(date_entry, 0, 3)

driver_a_label = QLabel("Количество водителей (Тип A):")
layout.addWidget(driver_a_label, 1, 0)
driver_a_entry = QLineEdit("10")
layout.addWidget(driver_a_entry, 1, 1)

driver_b_label = QLabel("Количество водителей (Тип B):")
layout.addWidget(driver_b_label, 1, 2)
driver_b_entry = QLineEdit("5")
layout.addWidget(driver_b_entry, 1, 3)

# Таблица для отображения расписания
schedule_scroll_area = QScrollArea()
schedule_table = QTableWidget()
schedule_scroll_area.setWidgetResizable(True)
schedule_scroll_area.setWidget(schedule_table)
layout.addWidget(schedule_scroll_area, 2, 0, 1, 4)

# Текст для вывода метрик
metrics_text = QLabel("")
metrics_text.setFont(QFont('Arial', 10))
layout.addWidget(metrics_text, 3, 0, 1, 4)

# Кнопка запуска алгоритмов
run_button = QPushButton("Создать расписание")
run_button.clicked.connect(execute_and_present)
layout.addWidget(run_button, 4, 0, 1, 4)

window.setLayout(layout)
window.show()
sys.exit(app.exec())

