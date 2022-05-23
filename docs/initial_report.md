# P2P Initial Report

## Information

Team name: **TBD**
GitLab repository: [`NSE-5`](https://gitlab.lrz.de/netintum/teaching/p2psec_projects_2022/NSE-5)
Names of team members:
 - Christian Plass (`ge96raf`)
 - Luis Kleinheinz (`ge96cek`)
Chosen module: NSE

## Implementation

**TBD**

## OS & Programming Language

We choose **GNU+Linux** as target operating system because it's free software with a huge documentation, preferably Debian GNU/Linux as distribution. Furthermore, it's the OS of our personal laptops and servers, so we are most familiar with it.
For the implementation language we choose **Python3** (at least v3.9) because of the great big standard library, as well as it's ease of development. We know of certain limitations of that language, e.g. the slow speed (compared to for example C++ or Rust) and no strictly enforced type system.

## Build system

This is not required for Python.

## Intended measures to guarantee quality of software

1. Enforcing code review of newly written (and tested) code by the other team member before merging feature branches into the master branch (this can be configured in repository settings).
2. Checking the code base with `pylint` and `flake8` to see violations of PEP-8 and some lighter forms of bad coding style.
3. Testing every commit with the self-written unittests using the `unittest` module. This should be done for every important code block to achieve a relatively high code coverage (almost 100% would be very nice, but 80% is still pretty good). We may even build some full end-to-end tests with full sample networks, but that's a question of available time and effort.

## Available libraries to assist in our project

Generally, the Python Standard Library is great and huge. We currently don't plan to use third-party libraries. However, if we needed to, we would search for them on PyPI to use `pip` as our package manager.

## License for your project’s software

[AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) since it's the strongest copyleft license out there (we would go for GPLv3 if this wasn't a network service). It allows anyone to read, edit, study and redistribute our code under the same license while prohibiting closed-source software builds.

## Previous programming experience

1. Luis (4. Bachelor Informatics)
    Fluent in Java
    Capable of C# and C
    (Currently no major Python experience, yet)
2. Chris (4. Bachelor Informatics)
    Very fluent in Python
    Capable of Java and C++
    Experienced in developing network services ([example](https://github.com/hopfenspace/MateBot))
    Working as a system administrator for a small company from Pfaffenhofen a.d. Ilm, participated in the Bachelor practical course _Systemadministration_
    GitHub: https://github.com/CrsiX

## Planned workload distribution

The goal is to achieve relatively equally distributed workloads.
Luis may work more on documenting and testing, while Chris may work more on developing.
Design choices should always be discussed with both team members.
Of course, the code base and program logic should be understood by both team members, otherwise documenting or testing wouldn't be reasonable possible.
