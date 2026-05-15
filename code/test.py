# usage of lambda 
people = [
    {"name": "A", "age": 25},
    {"name": "B", "age": 20},
]
def func(person):
    return person["age"]
people.sort(key = func)
