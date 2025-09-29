/**
 * @type {{name: string,first_name: string, last_name: string, employee_name:string, holiday_list: string, user_id: string, leaves: {from_date: string, to_date: string, employee: string, leave_type: string, half_day: boolean, half_day_date: string}[]}[]}
 */
const LEAVE_DATA = JSON.parse(window.leaveDataJSON);

const CURRENT_USER_DATA = findAndRemove(LEAVE_DATA, (e) => e.user_id === window.userId)

/**
 * @type {{[key: string]: {date: Date, description: string, holiday_date: string}[]}}
 */
const HOLIDAY_LISTS = JSON.parse(window.holidayListsJSON);
for (const list in HOLIDAY_LISTS) {
    for (const holiday of HOLIDAY_LISTS[list]) {
        holiday.date = parseUTCDate(holiday.holiday_date)
    }
}

/**
 * @type {{data_days_in_past: number, data_days_in_future: number, view_days_in_past: number, view_days_in_future: number}}
 */
const SETTINGS = JSON.parse(window.settingsJSON);

/**
 * @type {{leave_type: string, className: string, color: string, text: string}[]}
 */
const LEAVE_TYPES = JSON.parse(window.leaveTypesJSON);

const LEAVE_TYPE_CLASS_MAP = {}
const LEAVE_TYPE_TEXT_MAP = {}

for (const leaveType of LEAVE_TYPES) {
    LEAVE_TYPE_CLASS_MAP[leaveType.leave_type] = leaveType.className
    LEAVE_TYPE_TEXT_MAP[leaveType.leave_type] = leaveType.text
}

const WEEKDAY_FORMATTER = new Intl.DateTimeFormat(window.userLanguage || "en", {
    weekday: "short"
});
const MONTH_FORMATTER = new Intl.DateTimeFormat(window.userLanguage || "en", {
    month: "long"
});
const DAY_FORMATTER = new Intl.DateTimeFormat(window.userLanguage || "en", {
    day: "numeric"
});

/**
 * @type {{from: Date|null, to: Date|null, filter: string|null}}
 */
const CACHE = {
    from: null,
    to: null,
    filter: null,
};

// Elemente
const fromDateInput = document.getElementById("fromDate");
const toDateInput = document.getElementById("toDate");
const employeeNameFilterInput = document.getElementById("employeeNameFilter");
const gantt = document.getElementById('gantt');
const topScrollWrapper = document.getElementById('top-scroll-wrapper');
const topScrollContent = document.getElementById('top-scroll-content');

const TODAY = new Date(formatDateAsISO(new Date()))
const DATA_MAX_DATE = formatDateAsISO(new Date(Date.now() + SETTINGS.data_days_in_future * 24 * 60 * 60 * 1000))
const DATA_MIN_DATE = formatDateAsISO(new Date(Date.now() - SETTINGS.data_days_in_past * 24 * 60 * 60 * 1000))
fromDateInput.value = formatDateAsISO(new Date(Date.now() - SETTINGS.view_days_in_past * 24 * 60 * 60 * 1000));
fromDateInput.max = DATA_MAX_DATE
fromDateInput.min = DATA_MIN_DATE
toDateInput.value = formatDateAsISO(new Date(Date.now() + SETTINGS.view_days_in_future * 24 * 60 * 60 * 1000));
toDateInput.max = DATA_MAX_DATE
toDateInput.min = DATA_MIN_DATE

fromDateInput.addEventListener("change", onChange)
toDateInput.addEventListener("change", onChange)
employeeNameFilterInput.addEventListener("input", onChange)

gantt.onscroll = function () { topScrollWrapper.scrollLeft = gantt.scrollLeft; };
topScrollWrapper.onscroll = function () { gantt.scrollLeft = topScrollWrapper.scrollLeft; };

// Initial Load
onChange()


function onChange() {
    const fromVal = fromDateInput.value;
    const toVal = toDateInput.value;
    const from = parseUTCDate(fromVal);
    const to = parseUTCDate(toVal);
    const filter = employeeNameFilterInput.value

    if (!fromVal || !toVal) return;
    if (from > to) return;
    const datesChanged = from.valueOf() !== CACHE.from?.valueOf() || to.valueOf() !== CACHE.to?.valueOf()
    const filterChanged = CACHE.filter !== filter
    if (!datesChanged && !filterChanged) return;
    CACHE.from = from;
    CACHE.to = to;
    CACHE.filter = filter;

    renderDateColumns(from, to);
    const tableData = calcTableData(filter, from, to)
    renderTable(tableData)
}

/**
 *
 * @param {{name: string,first_name: string, last_name: string, employee_name:string,holiday_list: string,
 * row: ({
 *   from_date: Date;
 *   to_date: Date;
 *   start: Date;
 *   duration: number;
 *   employee: string;
 *   leave_type: string;
 *   half_day: 'start' | 'end' | null
 *   } | null)[]
 * }[]} tableData
 */
function renderTable(tableData) {
    const tableBody = document.getElementById('ganttBody')
    tableBody.innerHTML = '';
    for (const employee of tableData) {
        const tr = document.createElement("tr");

        const th = document.createElement("th");
        th.textContent = employee.employee_name;
        th.classList.add('text-truncate')
        tr.appendChild(th);
        for (const col of employee.row) {
            const td = document.createElement("td");
            if (col) {
                if (col.isHoliday) {
                    td.classList.add("holiday")
                } else {
                    td.colSpan = col.duration
                    const div = document.createElement("div");
                    if (col.half_day) {
                        div.classList.add('half-day-' + col.half_day)
                    }
                    div.classList.add(LEAVE_TYPE_CLASS_MAP[col.leave_type] || 'default-leave')
                    div.textContent = LEAVE_TYPE_TEXT_MAP[col.leave_type] || col.leave_type.substring(0, 3)
                    div.title = col.leave_type
                    td.appendChild(div)
                }

            }
            tr.appendChild(td);
        }
        tableBody.appendChild(tr);
    }
    topScrollContent.style.width = gantt.scrollWidth + 'px';
}

/**
 *
 * @param {string} filter
 * @param {Date} from
 * @param {Date} to
 */
function calcTableData(filter, from, to) {
    const filteredEmployees = []
    if (CURRENT_USER_DATA) {
        filteredEmployees.push(CURRENT_USER_DATA)
    }
    if (filter) {
        filteredEmployees.push(
            ...LEAVE_DATA.filter((employee) =>
                employee.employee_name.toLowerCase().indexOf(filter.toLowerCase()) !== -1
            ))
    } else {
        filteredEmployees.push(...LEAVE_DATA)
    }
    const data = []
    const dates = getDatesBetween(from, to);
    for (const employee of filteredEmployees) {
        const entries = [];
        for (const leave of employee.leaves) {
            const result = getLeaveInFrame(leave, from, to);
            if (result) {
                entries.push(result);
            }
        }
        entries.sort((a, b) => a.from_date.valueOf() - b.from_date.valueOf());

        const row = new Array(dates.length).fill(null);
        let entriesIndex = 0;
        const holidays = HOLIDAY_LISTS[employee.holiday_list]
        let holidayIndex = holidays.findIndex(h => h.date.valueOf() >= from)
        if (holidayIndex >= 0) {
            //assumption: holiday list has only unique days
            for (let i = 0; i < dates.length; i++) {
                if (
                    holidays[holidayIndex].date.valueOf() === dates[i].valueOf()
                ) {
                    row[i] = { ...holidays[holidayIndex], isHoliday: true };
                    holidayIndex++;
                    if (holidayIndex === holidays.length) {
                        break;
                    }
                }
            }
        }
        //assumption: leave applications have no overlap
        let iR = 0
        for (let i = 0; i < dates.length; i++) {
            if (
                entriesIndex < entries.length &&
                entries[entriesIndex].start.valueOf() === dates[i].valueOf()
            ) {
                row.splice(i - iR, entries[entriesIndex].duration, entries[entriesIndex]);
                iR += entries[entriesIndex].duration - 1
                i = i + entries[entriesIndex].duration - 1
                entriesIndex += 1;
            }
        }
        data.push({ "employee_name": employee.employee_name, "row": row })
    }
    return data;
}

/**
 *
 * @param {{from_date: string, to_date: string, employee: string, leave_type: string, half_day: boolean, half_day_date: string}} leave
 * @param {Date} frameFrom
 * @param {Date} frameTo
 */
function getLeaveInFrame(leave, frameFrom, frameTo) {
    const leaveFrom = parseUTCDate(leave.from_date);
    const leaveTo = parseUTCDate(leave.to_date);

    // 1) Berechne die Schnitt­grenzen
    const start = leaveFrom > frameFrom ? leaveFrom : frameFrom;
    const end = leaveTo < frameTo ? leaveTo : frameTo;

    // 2) Kein Über­schnitt, wenn Start nach Ende liegt
    if (start > end) return;
    let half_day = null
    if (leave.half_day) {
        const half_day_date = parseUTCDate(leave.half_day_date)
        if (half_day_date.valueOf() === start.valueOf()) {
            half_day = 'start'
        } else if (half_day_date.valueOf() === end.valueOf()) {
            half_day = 'end'
        }

    }
    const duration = getDiffInDays(start, end) + 1;
    return { ...leave, from_date: leaveFrom, to_date: leaveTo, start, duration, half_day };
}

/**
 *
 * @param {Date} from
 * @param {Date} to
 * @returns
 */
function renderDateColumns(from, to) {
    const headerRow = document.querySelector("#ganttHeader tr");
    while (headerRow.children.length > 1) {
        headerRow.removeChild(headerRow.lastChild);
    }

    const colgroup = document.getElementById("ganttColgroup");
    while (colgroup.children.length > 1) {
        colgroup.removeChild(colgroup.lastChild);
    }

    const dates = getDatesBetween(from, to);
    dates.forEach((date) => {
        const th = document.createElement("th");
        th.innerHTML = `<small>${WEEKDAY_FORMATTER.format(date)}</small><br>${DAY_FORMATTER.format(date)}`

        const col = document.createElement("col")
        col.classList.add("day")

        if (date.valueOf() === TODAY.valueOf()) {
            th.classList.add("today")
            col.classList.add("today")
        }
        headerRow.appendChild(th);
        colgroup.appendChild(col);


    });
}

/**
 * Formatiert Date als "YYYY-MM-DD"
 * @param {Date} date
 * @returns string
 */
function formatDateAsISO(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

/**
 *
 * @param {Date} startDate
 * @param {Date} endDate
 */
function getDiffInDays(firstDay, lastDay) {
    return (lastDay.valueOf() - firstDay.valueOf()) / (1000 * 60 * 60 * 24);
}

/**
 *
 * @param {Date} start
 * @param {Date} end
 * @returns
 */
function getDatesBetween(start, end) {
    const dates = [];
    const curr = new Date(start);
    while (curr <= end) {
        dates.push(new Date(curr));
        curr.setUTCDate(curr.getUTCDate() + 1);
    }
    return dates;
}

/**
 * Finds the first element in the array that satisfies the given predicate,
 * removes it from the array, and returns it.
 *
 * @template T
 * @param {T[]} array - The array to search and modify.
 * @param {(item: T, index: number, array: T[]) => boolean} predicate - A function to test each element.
 * @returns {T | null} The found element, or null if none was found.
 */
function findAndRemove(array, predicate) {
    const index = array.findIndex(predicate);
    if (index !== -1) {
        return array.splice(index, 1)[0];
    }
    return null;
}

/**
 * Parse of "YYYY-MM-DD" into a UTC Date.
 * @param {string} s — e.g. "2025-07-24"
 * @returns {Date}
 */
function parseUTCDate(s) {
    const y = Number(s.slice(0, 4));
    const m = Number(s.slice(5, 7)) - 1;  // zero‑based month
    const d = Number(s.slice(8, 10));
    return new Date(Date.UTC(y, m, d));
}