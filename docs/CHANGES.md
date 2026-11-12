# Test file changes

Line numbers refer to the uploaded files. Rows with several tests are the same change at each listed line.

## All four files

| File | Test | Before | After | Reason | Tag |
|---|---|---|---|---|---|
| pa1 | module level | no `TIERS` | `TIERS = {1: ["test_extra_create_post", "test_extra_post_comment", "test_extra_edit_comment"], 2: ["test_extra_upvote_post", "test_extra_upvote_default", "test_extra_sorting_posts"]}` | Required by the spec, plus the new default-upvote test | |
| pa1, pa2, pa3, pa4 | `__main__` block | `Thread(target=run_tests)`, with `app.run(...)` in the main thread | `app.run` in a daemon thread, then `run_tests()` in the main thread | The file never exited after the tests. Listed for PA1; the same bug is in the other three. | |

## Tiers and PA2 fixes from the challenge handouts

| File | Test | Before | After | Reason | Tag |
|---|---|---|---|---|---|
| pa2 | module level | no `TIERS` | `TIERS = {1: ["test_extra_create_user", "test_extra_get_user", "test_extra_get_user_unauthorized", "test_extra_send_money", "test_extra_send_money_unauthorized"]}` | Handout Tier I (passwords). Tier II (hashing) and Tier III have no tests. | |
| pa3 | module level | no `TIERS` | `TIERS = {1: ["test_extra_create_friends", "test_extra_get_friends"], 2: ["test_join"]}` | Handout Tier I (friends) and Tier II (join). Tier III has no tests. | |
| pa4 | module level | no `TIERS` | Tier 1: the 4 drop tests and 2 update-assignment tests. Tier 2: the 4 submit tests and 4 grade tests. | Handout Tier I and Tier II. Tier III has no tests. | |
| pa3, pa4 | module level | no `TIER_BONUS` | `TIER_BONUS = {2: 1}` | Handout: Tier II is worth +1 more when Tier I is also earned. `grade.py` now reads this setting. | |
| pa2 | `_create_user_and_assert_balance`, `_get_user_and_assert_balance` (affects all 5 extra tests) | response must contain the plain-text password | `password` is skipped in the response comparison | The handout never asks for it, and Tier II hashing rules it out. Correct submissions failed all 5 tests. | EXPECTATION CHANGE |
| pa2 | test_extra_get_user_unauthorized, test_extra_send_money, test_extra_send_money_unauthorized | password read back from the response with `user.get("password")` | `EXTRA_SAMPLE_USER["password"]` | Same reason | EXPECTATION CHANGE |
| pa2 | test_extra_create_user | no check for a missing password | POST without a password must return 401 | Handout: 401 if no password is sent | EXPECTATION CHANGE |
| pa2 | test_extra_get_user_unauthorized | only a wrong password was checked | POST with `{}` must also return 401 | Same | EXPECTATION CHANGE |
| pa2 | test_extra_send_money_unauthorized | only a wrong password was checked | send without a password must also return 401 | Same | EXPECTATION CHANGE |

## pa1_test.py

| Test (line) | Before | After | Reason | Tag |
|---|---|---|---|---|
| test_get_initial_posts (115), test_create_post (142), test_extra_create_post (531), test_extra_sorting_posts (869, 897) | `status_code_error(res, route, ...)` | `status_code_error(req_type, route, ...)` | Known bug a: response object passed as the request type | |
| test_extra_upvote_post (828) | `wrong_value_error(req_type, route, upvotes_to_add + old_upvotes, new_upvotes, ...)` | `wrong_value_error(req_type, route, new_upvotes, upvotes_to_add + old_upvotes, ...)` | Known bug b: actual and expected swapped | |
| test_get_invalid_post (287), test_delete_invalid_post (312) | `err_res = res.json()` | `err_res = res.json().get("error")` | The check could never fail, because the body was already known to be a dict. The message requires `{"error": ...}`. | EXPECTATION CHANGE |
| test_get_comments_invalid_post (453), test_post_invalid_comment (480), test_extra_create_post (511), test_extra_post_comment (644), test_extra_edit_comment (764) | `res_error = res.json()` | `res_error = res.json().get("error")` | Same as above | EXPECTATION CHANGE |
| test_edit_comment (after 416), test_extra_edit_comment (after 747) | result of `is_jsonable` ignored, then `res.json()` | added `self.assertTrue(jsonable, comment_create_err)` | A non-JSON reply crashed the test instead of showing the intended message. Pass or fail is unchanged. | |
| test_extra_post_comment (after 680) | GET to the core route, reported with the extra route | added `route = gen_comments_route(post_id)` | The failure message named a route that was not called | |

| test_extra_upvote_default (new test) | no check of a POST with no body | new test: `POST /api/extra/posts/{id}/` with no body must return 200 and add 1 upvote. Added to Tier 2. | Handout: with no post body, upvotes go up by 1. PA1 extra-credit count goes from 5 to 6. | EXPECTATION CHANGE |
| test_extra_create_post, test_extra_post_comment, test_extra_edit_comment, test_extra_upvote_post, test_extra_sorting_posts | `SAMPLE_POST`, with link `cornellappdev.com` | new `EXTRA_SAMPLE_POST`, with link `https://cornellappdev.com` | A student validating URLs strictly failed the old link. Core tests still use `SAMPLE_POST`. | EXPECTATION CHANGE |

## pa2_test.py

| Test (line) | Before | After | Reason | Tag |
|---|---|---|---|---|
| test_delete_user (211, 225), test_get_invalid_user (359), test_delete_invalid_user (365) | `route = gen_users_path(...)` | `route = gen_users_route(...)` | Messages showed a full URL as the route | |
| `_get_user_and_assert_balance` (282) | `route = gen_users_path(user_id, extra=extra)` | `route = gen_users_route(user_id, extra=extra)` | Same | |
| `_send_money` (315) | `route = gen_send_path(extra=extra)` | `route = gen_send_route(extra=extra)` | Same | |

## pa3_test.py

| Test (line) | Before | After | Reason | Tag |
|---|---|---|---|---|
| test_overdraw_send (908) | message expects balance 20 | message expects 10 | The assertion expects 10 | |
| test_change_denied_transaction (1019) | message expects balance 10 | message expects 0 | The assertion expects 0 | |
| test_change_denied_transaction (1050) | message expects balance 10 | message expects 20 | The assertion expects 20 | |
| test_get_user_transactions (806) | `req_type = "POST"` | `req_type = "GET"` | The only request it reports on is a GET | |
| test_get_user_transactions (855, 856) | `wrong_value_error(req_type, route, tr.get(key), te.get(key), te.get(key))` | `wrong_value_error(req_type, route, te.get(key), tr.get(key), key)` | Actual and expected swapped; the value was used as the field name | |
| test_join (1168) | last argument `te.get(key)` | last argument `key` | The value was used as the field name | |
| test_extra_create_friends (1096, 1105) | friends-length message reported `req_type, route` from the earlier POST | reports `"GET"` and the friends route for that user | The message named the wrong request | |
| test_delete_user (242, 267), test_get_invalid_user (286), test_delete_invalid_user (292) | `route = gen_users_path(...)` | `route = gen_users_route(...)` | Messages showed a full URL as the route | |
| test_accept_request (582), test_deny_request (702), test_overdraw_accept (936), test_change_accepted_transaction (987), test_change_denied_transaction (1010) | `jsonable_test(..., transaction_body)` | `jsonable_test(..., {"accepted": True})` or `{"accepted": False}`, matching the request | The message showed a body that was not sent | |
| test_send_money, test_request_payment, test_accept_request, test_deny_request, test_change_denied_transaction (14 lines: 357, 398, 439, 474, 514, 554, 594, 634, 674, 714, 753, 792, 1033, 1064) | `wrong_value_error(..., key, transaction_body[key])` | `wrong_value_error(..., key, transaction_body)` | Wrong helper argument: a single value passed as the request body | |
| test_send_money, test_request_payment, test_accept_request, test_deny_request, test_overdraw_send, test_overdraw_accept, test_change_denied_transaction (14 places, each before `res1 = requests.get(...)` or `res2 = requests.get(...)`) | balance messages reported the earlier POST to the transactions route | added `req_type, route = "GET", gen_users_route(user1)` (or `user2`) | The message named the wrong request | |

## pa4_test.py

| Test (line) | Before | After | Reason | Tag |
|---|---|---|---|---|
| test_extra_update_assignment (1176) | `def text_extra_update_assignment` | `def test_extra_update_assignment` | Known bug d: it never ran | EXPECTATION CHANGE |
| test_extra_update_assignment (1217, 1220) | `update_assignment_body["key"]` | `update_assignment_body[key]` | Known bug e: KeyError for every student | EXPECTATION CHANGE |
| test_delete_course (291) | `requests.get(gen_users_path(course_id))` | `requests.get(gen_courses_path(course_id))` | Known bug f: it checked a user, not the deleted course | EXPECTATION CHANGE |
| test_extra_drop_invalid_course (1089) | `gen_courses_path(user_id)` | `gen_courses_path(1000)` | Known bug g: it could hit a real course | EXPECTATION CHANGE |
| test_add_student_to_course (406), test_add_instructor_to_course (621) | `course.get("id") is not None` | `user.get("id") is not None` | The user-id check tested the course. Pass or fail is unchanged, because `user["id"]` raised next. | |
| test_add_student_to_course (458, 520) | message used `course.get(key)` | `student.get(key)` | The message showed the wrong value | |
| test_add_instructor_to_course (673, 736) | message used `course.get(key)` | `instructor.get(key)` | Same | |
| test_add_student_to_course (559), test_add_instructor_to_course (776) | message used `user.get(key)` | `course.get(key)` | Same | |
| test_add_instructor_to_course (656) | `"type of instructors field"` | `"type of students field"` | The check is on students | |
| test_add_instructor_to_course (664) | `"length of students list"` | `"length of instructors list"` | The check is on instructors | |
| test_get_course (183), test_get_user (344) | `req_type = "GET"` before a POST | `req_type = "POST"` | The message named the wrong method | |
| test_get_course (after 189, 191) | GET reported with the collection route and a body | added `req_type = "GET"` and `route = gen_courses_route(course_id)`; removed the body argument | The message named the wrong request | |
| test_get_user (after 349, 351) | Same | added `req_type = "GET"` and `route = gen_users_route(user_id)`; removed the body argument | Same | |
| test_delete_course (252, 290) | `route = gen_courses_path(course_id)` | `route = gen_courses_route(course_id)` | Messages showed a full URL as the route | |
| test_add_student_to_course (478), test_add_instructor_to_course (694) | `route = gen_courses_route()` | `route = gen_courses_route(course_id)` | The message named the wrong route | |
| test_add_student_to_course (after 539, 541), test_add_instructor_to_course (after 756, 758), test_extra_drop_course (after 1038, 1040) | GET of a user reported with an old route and a body | added `route = gen_users_route(user_id)`; removed the body argument | The message named the wrong request | |
| test_create_assignment_for_course (828), test_create_bad_assignment_for_course (920), test_extra_update_assignment (1199), test_extra_submit (1302), test_extra_submit_invalid_user (1386), test_extra_submit_invalid_assignment_for_user (1446), test_extra_grade (1506), test_grade_invalid_submission (1641), test_grade_wrong_submission_assignment (1707, 1717) | `route = gen_courses_route(course_id)` | `route = gen_courses_route(course_id) + "assignment/"` | The message named the wrong route | |
| test_create_assignment_invalid_course (957) | `req_type = "GET"` | `req_type = "POST"` | The request is a POST | |
| test_extra_drop_course (1034) | `"length of courses filed"` | `"length of courses field"` | Typo in the message | |
| 17 tests: test_create_bad_course, test_create_bad_user, test_create_bad_assignment_for_course, test_get_invalid_course, test_get_invalid_user, test_add_user_invalid_course, test_create_assignment_invalid_course, test_extra_drop_invalid_course, test_extra_drop_invalid_user, test_extra_drop_user_not_in_course, test_extra_update_invalid_assignment, test_extra_submit_invalid_assignment, test_extra_submit_invalid_user, test_extra_submit_invalid_assignment_for_user, test_grade_invalid_assignment, test_grade_invalid_submission, test_grade_wrong_submission_assignment | `assertIsNotNone(res.json()["error"], wrong_value_error(req_type, route, res.json()["error"], str, "error", "type of error field"))` | `assertIsNotNone(res.json().get("error"), wrong_value_error(req_type, route, res.json().get("error"), str, "type of error field"))` | A missing key raised KeyError instead of the assertion message, and the field name argument was wrong. Pass or fail is unchanged. | |

## pa5_test.py

New file. The course gives no PA5 test file, because graders run `docker-compose up -d` and try the route named in the README. This file does those steps for the grader, in the same format as the others. It sets `DOCKER = True`, so the grader starts the submission with `docker compose up -d` instead of importing `app.py`.

The core tests follow the grader's PA5 rubric, set in `RUBRIC` with each test's points (10 in total). `EXTRA_CREDIT_NEEDS` gives extra credit only when `test_container_starts` passes.

| Test | Points | Checks |
|---|---|---|
| test_dockerfile_in_src | 1 | `Dockerfile` in `src` |
| test_dockerfile_installs_requirements | 1 | a `RUN pip install -r requirements.txt` line |
| test_dockerfile_starts_app | 1 | a `CMD` or `ENTRYPOINT` line |
| test_compose_in_src | 1 | `docker-compose.yml` in `src` |
| test_compose_uses_docker_hub_image | 1 | an `image:` named `<username>/<repository>` |
| test_compose_publishes_port | 1 | a `ports:` entry |
| test_container_starts | 2 | `docker compose up -d` worked and the app answers |
| test_route_returns_json | 2 | a GET route from the README, or `/api/courses/`, returns JSON with a status below 500 |
| test_extra_python_distribution (Tier 1) | +1 | the final `FROM` is not the basic `python[:version]` image. The README explanation is not checked. |
| test_extra_gunicorn_requirement (Tier 2) | | `requirements.txt` lists gunicorn |
| test_extra_start_server_script (Tier 2) | | `start_server.sh` runs gunicorn with 4 workers |
| test_extra_dockerfile_runs_script (Tier 2) | | the Dockerfile's `CMD` or `ENTRYPOINT` runs `start_server.sh` |
| test_extra_gunicorn_serves_app (Tier 2) | +1 | the running container answers with gunicorn's `Server` header |

`TIER_BONUS = {2: 1}`, as in the handout.

`README_FIELDS` and `README_QUESTIONS` list the README template's fields and questions. The grader takes off 0.5 for each one left blank. `Challenges Attempted` is not listed, because a student who tried no challenges may leave it blank.

## pa6_test.py

New file. The course gives no PA6 test file. Graders visit the server address from the README. This file does that in the same format as the others. It sets `REMOTE = True`, so the grader runs the tests without starting `app.py` or Docker, and passes the student's folder name as the NetID. `NO_CHALLENGES = True` because PA6 has no extra credit. `README_FIELDS` and `README_QUESTIONS` list the README template's fields and questions, each −0.5 when blank.

| Test | Points | Checks |
|---|---|---|
| test_server_is_reachable | 3 | the README's server address answers |
| test_base_endpoint | 2 | `GET /` returns 200 and `"<netid> was here!"` |
| test_working_endpoint | 2 | a GET route from the README, or `/api/courses/`, returns JSON with a status below 500 |
| test_env_file | 1 | `src/.env` contains the NetID |
| test_netid_read_from_env | 1 | `app.py` uses `getenv`, `environ`, or dotenv, and doesn't hardcode `"<netid> was here"` |
| test_deployment_files | 1 | `Dockerfile`, `docker-compose.yml`, and `.dockerignore` in `src` |

## Noticed and left alone

- pa2: debug `print` calls in `_get_user_and_assert_balance`, `_send_money`, and test_extra_get_user_unauthorized. They do not affect results.
- pa1 `from requests.api import post`, pa3 `from re import L` and `from datetime import datetime`: unused imports that do no harm.
- pa1 test_extra_post_comment (668-678): a leftover error-format check after a successful POST. It cannot fail, and the spec says not to remove checks.
- pa3 `test_join` and pa4 `test_grade_*`: not named `test_extra_*`, but they are extra credit by the guard rule and their names are not misspelled.
