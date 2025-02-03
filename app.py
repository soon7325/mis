import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash


app = Flask(__name__)
app.secret_key = '8888'

def load_data():
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/', methods=['GET', 'POST'])
def student_signin():
    data = load_data()
    student = None

    if request.method == 'POST':
        name = request.form.get('name')
        student = next((s for s in data['students'] if s['name'] == name), None)
        if student:
            ip_address = request.remote_addr
            student['ip'] = ip_address
            save_data(data)
            return redirect(url_for('student_course', student_name=student['name']))
        else:
            flash("Student not found.", 'error')

    return render_template('student_signin.html', student=student, data=data)

@app.route('/student_course/<student_name>')
def student_course(student_name):
    data = load_data()
    student = next((s for s in data['students'] if s['name'] == student_name), None)
    if not student:
        return "Student not found."

    courses = [c for c in data['courses'] if c['name'] in student.get('courses', [])]

    return render_template('student_course.html', student=student, courses=courses)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher_dashboard():
    data = load_data()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'clear_ip':
            student_name = request.form.get('student_name')
            for student in data['students']:
                if student['name'] == student_name:
                    student['ip'] = None
                    break
            save_data(data)
            flash(f"IP address for {student_name} cleared.", 'info')
        elif action == 'add_course':
            course_name = request.form.get('course_name')
            time = request.form.get('time')
            classroom = request.form.get('classroom')
            new_course = {
                'name': course_name,
                'time': time,
                'classroom': classroom,
                'students': []
            }
            data['courses'].append(new_course)
            save_data(data)
            flash(f"Course {course_name} added.", 'success')
        elif action == 'bind_course':
            student_name = request.form.get('student_name')
            course_name = request.form.get('course_name')
            for student in data['students']:
                if student['name'] == student_name:
                    if 'courses' not in student:
                        student['courses'] = []
                    if course_name not in student['courses']: #避免重复绑定
                        student['courses'].append(course_name)
                    break
            for course in data['courses']:
                if course['name'] == course_name:
                    if 'students' not in course:
                        course['students'] = []
                    if student_name not in course['students']: #避免重复添加
                        course['students'].append(student_name)
                    break
            save_data(data)
            flash(f"Course {course_name} bind to {student_name}.", 'success')
    return render_template('teacher_dashboard.html', data=data)

@app.route('/classroom_info/<course_name>/<time>/<classroom>')
def classroom_info(course_name, time, classroom):
    data = load_data()
    course = next((c for c in data['courses'] if c['name'] == course_name and c['time'] == time and c['classroom'] == classroom), None)
    if course:
        return render_template('classroom_info.html', course=course)
    else:
        return "Course information not found."

# 教室日程
@app.route('/classroom_schedule/<time_slot>', methods=['GET', 'POST'])
def classroom_schedule(time_slot):
    data = load_data()
    schedule = {}
    temp_courses = {}  # 用于存储临时课程
    log_file = 'log/temp_courses.json'

    # 尝试加载日志数据
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            if time_slot in log_data:
                temp_courses = log_data[time_slot]

    for i in range(1, 7):
        room_name = f"Room {i}"
        schedule[room_name] = None
        for course in data['courses']:
            if course['classroom'] == room_name and course['time'] == time_slot:
                schedule[room_name] = course
                break

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_temp_course':
            classroom = request.form.get('classroom')
            course_name = request.form.get('course_name')

            if not (classroom in temp_courses and temp_courses[classroom]): #避免重复添加同一教室的课程
                temp_courses[classroom] = {'name': course_name}
                flash(f"Course {course_name} added to {classroom}.", 'success')

                # 记录日志
                log_data = {}
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)

                log_data[time_slot] = temp_courses

                if not os.path.exists('log'):
                    os.makedirs('log')

                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=4)
            else:
                flash(f"Classroom {classroom} is already occupied.", 'info')

            return redirect(url_for('classroom_schedule', time_slot=time_slot))

        return redirect(url_for('classroom_schedule', time_slot=time_slot))

    return render_template('classroom_schedule.html', time_slot=time_slot, schedule=schedule, data=data, temp_courses=temp_courses)


@app.route('/admin', methods=['GET'])
def admin():
    return render_template('admin.html')

@app.route('/admin/students', methods=['GET', 'POST'])
def admin_students():
    data = load_data()
    if request.method == 'POST':
        name = request.form['name']
        ic_number = request.form['ic_number']
        for student in data['students']:
            if student['name'] == name:
                student['ic_number'] = ic_number
                break
        save_data(data)
        return redirect(url_for('admin_students'))
    return render_template('admin_students.html', data=data)

@app.route('/admin/courses', methods=['GET', 'POST'])
def admin_courses():
    data = load_data()
    schedule = {}
    for i in range(1, 7):
        room_name = f"Room {i}"
        schedule[room_name] = None
        for course in data['courses']:
            if course['classroom'] == room_name and course['time'] == request.form.get('time'):
                schedule[room_name] = course
                break

    if request.method == 'POST':
        course_name = request.form['course_name']
        time = request.form['time']
        classroom = request.form['classroom']

        # 检查时间冲突
        conflict = False
        for c in data['courses']:
          if c['classroom'] == classroom and c['time'] == time:
            conflict = True
            break
        if conflict:
          flash("时间冲突，请选择其他教室或时间")
          return redirect(url_for('admin_courses'))

        data['courses'].append({
            'name': course_name,
            'time': time,
            'classroom': classroom
        })
        save_data(data)
        return redirect(url_for('admin_courses'))
    return render_template('admin_courses.html', schedule=schedule, time_slot=request.form.get('time')) # 将 time_slot 传递给模板


@app.route('/admin/workshops', methods=['GET', 'POST'])
def admin_workshops():
    data = load_data()
    schedule = {}
    for i in range(1, 7):
        room_name = f"Room {i}"
        schedule[room_name] = None
        for course in data['courses']:
            if course['classroom'] == room_name and course['time'] == request.form.get('time'):
                schedule[room_name] = course
                break

    if request.method == 'POST':
        course_name = request.form['course_name']
        time = request.form['time']
        classroom = request.form['classroom']
        day = request.form['day']

        # 检查时间冲突
        conflict = False
        for c in data['courses']:
          if c['classroom'] == classroom and c['time'] == time:
            conflict = True
            break
        if conflict:
          flash("时间冲突，请选择其他教室或时间")
          return redirect(url_for('admin_workshops'))

        data['courses'].append({
            'name': course_name,
            'time': time,
            'classroom': classroom,
            'day': day,
            'workshop': True
        })
        save_data(data)
        return redirect(url_for('admin_workshops'))
    return render_template('admin_workshops.html', schedule=schedule, time_slot=request.form.get('time')) # 将 time_slot 传递给模板


@app.route('/workshop', methods=['GET', 'POST'])
def workshop():
    data = load_data()
    workshops = [course for course in data['courses'] if 'workshop' in course]
    if request.method == 'POST':
        ic_number = request.form['ic_number']
        workshop_name = request.form['workshop']
        for student in data['students']:
            if student['ic_number'] == ic_number:
                name = student['name']
                # 处理Workshop报名逻辑，例如将学生添加到Workshop的报名列表中
                break
        return render_template('workshop.html', workshops=workshops, name=name)
    return render_template('workshop.html', workshops=workshops)


if __name__ == '__main__':
    app.run(debug=True)