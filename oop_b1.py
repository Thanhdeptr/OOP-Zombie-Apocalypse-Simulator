class Student:
    _next_id = 1

    def __init__(self, name, age, major):
        self.id = Student._next_id
        Student._next_id += 1
        self.ten = name
        self.tuoi = age
        self.nganh = major
    def print_info(self):
        print(f"MSSV: {self.id}, Ten: {self.ten}, Tuoi: {self.tuoi}, Nganh: {self.nganh}")
student1 = Student("Nguyen Van A", 20, "CNTT")
student2 = Student("Nguyen Van B", 21, "law")
Student.print_info(student1)
Student.print_info(student2)