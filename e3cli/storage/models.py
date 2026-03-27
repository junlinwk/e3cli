"""資料模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Course:
    id: int
    shortname: str
    fullname: str


@dataclass
class Assignment:
    id: int
    course_id: int
    course_name: str
    name: str
    duedate: int  # Unix timestamp, 0 = 無截止日
    status: str = "new"  # new, draft, submitted


@dataclass
class CourseFile:
    course_id: int
    module_id: int
    filename: str
    fileurl: str
    filesize: int
    time_modified: int
