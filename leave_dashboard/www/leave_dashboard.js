/** @typedef {{from_date: string, from_time: "Morning" | "Noon", to_date: string, to_time: "Noon" | "Evening", employee: string, leave_type: string}} RawLeave */

/** @typedef {{name: string,first_name: string, last_name: string, employee_name:string, branch: string, user_id: string, holiday_weekdays: {[key: string]: true} leaves: RawLeave[]}} RawEmployee */

/**
 * @type {RawEmployee[]}
 */
const LEAVE_DATA = JSON.parse(window.leaveDataJSON);

const CURRENT_USER_DATA = findAndRemove(LEAVE_DATA, (e) => e.user_id === window.userId)

/** @typedef {{country_holidays: {[key: string]: string}, custom_holidays: {[key: string]:{date: string, label: string, time: "Morning -> Evening" | "Morning -> Noon" | "Noon -> Evening"}}}} HolidayList */

/**
 * @type {{[key: string]: HolidayList}}
 */
const HOLIDAY_LISTS = JSON.parse(window.holidayListsJSON);

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
        th.classList.add('employee-col')
        tr.appendChild(th);
        for (const col of employee.row) {
            const td = document.createElement("td");
            if (col) {
                td.colSpan = col.duration * 2
                if (col.isHoliday) {
                    td.classList.add("holiday")
                } else if (col.isLeave) {
                    const div = document.createElement("div");
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

        const row = new Array(dates.length * 2).fill(null);
        const holidays = HOLIDAY_LISTS[employee.branch]

        //assumption: leave applications have no overlap
        let entriesIndex = 0;
        let iC = 0;
        for (let i = 0; i < row.length; i++) {
            const date = dates[((i + iC) / 2) | 0]
            const time = (i + iC) % 2 === 0 ? "Morning" : "Noon"
            // Leaves
            if (
                entriesIndex < entries.length &&
                entries[entriesIndex].start.valueOf() === date.valueOf() &&
                entries[entriesIndex].startTime === time
            ) {
                row.splice(i, entries[entriesIndex].duration * 2, { ...entries[entriesIndex], isLeave: true });
                iC += (entries[entriesIndex].duration * 2) - 1;
                entriesIndex += 1;
                continue
            }
            // Holidays
            YMD = formatDateAsUTCISO(date)
            if (employee.holiday_weekdays[YMD]) {
                if (time === "Noon" && row[i - 1]?.isHoliday) {
                    row.splice(i - 1, 2, { isWeeklyHoliday: true, isHoliday: true, duration: 1 });
                    iC += 1;
                    i -= 1;
                } else {
                    row[i] = { isWeeklyHoliday: true, isHoliday: true, duration: 0.5 }
                }
                continue
            }
            let holiday = holidays.country_holidays[YMD]
            if (holiday) {
                if (time === "Noon" && row[i - 1]?.isHoliday) {
                    row.splice(i - 1, 2, { label: holiday, isHoliday: true, duration: 1 });
                    iC += 1;
                    i -= 1;
                } else {
                    row[i] = { label: holiday, isHoliday: true, duration: 0.5 }
                }
                continue
            }
            let custom_holiday = holidays.custom_holidays[YMD]
            if (custom_holiday && !((custom_holiday.time === "Noon -> Evening" && time === "Morning") || custom_holiday.time === "Morning -> Noon" && time === "Noon")) {
                if (time === "Noon" && row[i - 1]?.isHoliday) {
                    row.splice(i - 1, 2, { ...custom_holiday, isHoliday: true, duration: 1 });
                    iC += 1;
                    i -= 1;
                } else {
                    row[i] = { ...custom_holiday, isHoliday: true, duration: 0.5 }
                }
                continue
            }

            //combine half-days to one if nothing in
            if (time == "Noon" && row[i - 1] === null) {
                row.splice(i - 1, 2, { duration: 1 });
                iC += 1;
                i -= 1;
            }
        }
        data.push({ "employee_name": employee.employee_name, "row": row })
    }
    return data;
}

/**
 *
 * @param {RawLeave} leave
 * @param {Date} frameFrom
 * @param {Date} frameTo
 */
function getLeaveInFrame(leave, frameFrom, frameTo) {
    const leaveFrom = parseUTCDate(leave.from_date);
    const leaveTo = parseUTCDate(leave.to_date);
    let start = leaveFrom
    let end = leaveTo
    let startTime = leave.from_time
    let endTime = leave.to_time

    if (leaveFrom > frameTo || leaveTo < frameFrom) {
        return
    }
    if (leaveFrom < frameFrom) {
        start = frameFrom;
        startTime = "Morning";
    }
    if (leaveTo > frameTo) {
        end = frameTo;
        endTime = "Evening";
    }

    let duration = getDiffInDays(start, end) + 1;
    if (startTime == "Noon") duration -= 0.5
    if (endTime == "Noon") duration -= 0.5
    return { ...leave, from_date: leaveFrom, to_date: leaveTo, start, end, startTime, endTime, duration };
}

/**
 *
 * @param {Date} from
 * @param {Date} to
 * @returns
 */
function renderDateColumns(from, to) {
    const monthRow = document.querySelector("#ganttHeader tr#month");
    while (monthRow.children.length > 1) {
        monthRow.removeChild(monthRow.lastChild);
    }

    const dayRow = document.querySelector("#ganttHeader tr#day");
    dayRow.replaceChildren()

    const colgroup = document.getElementById("ganttColgroup");
    while (colgroup.children.length > 1) {
        colgroup.removeChild(colgroup.lastChild);
    }

    const dates = getDatesBetween(from, to);
    dates.forEach((date) => {
        // New Month
        if (date.valueOf() === from.valueOf() || date.getUTCDate() === 1) {
            const month = document.createElement("th");
            const numberOfDays = 1 + Math.min(getDiffInDays(date, lastDayOfMonth(date)), getDiffInDays(date, to))
            month.colSpan = numberOfDays * 2
            month.classList.add("month")
            month.innerHTML = MONTH_FORMATTER.format(date)
            monthRow.append(month)
        }
        const day = document.createElement("th");
        day.innerHTML = `<small>${WEEKDAY_FORMATTER.format(date)}</small><br>${DAY_FORMATTER.format(date)}`
        day.colSpan = 2
        day.classList.add("date")

        const col = document.createElement("col")
        col.classList.add("half-day")

        if (date.valueOf() === TODAY.valueOf()) {
            day.classList.add("today")
            col.classList.add("today")
        }
        dayRow.appendChild(day);
        colgroup.appendChild(col);
        colgroup.appendChild(col.cloneNode());
    });
}

/**
 * Format Date as "YYYY-MM-DD"
 * @param {Date} date
 * @returns string
 */
function formatDateAsISO(date) {
    return date.getFullYear() + "-" +
        String(date.getMonth() + 1).padStart(2, "0") + "-" +
        String(date.getDate()).padStart(2, "0");
}

/**
 * Format Date as UTC "YYYY-MM-DD"
 * @param {Date} date
 * @returns string
 */
function formatDateAsUTCISO(date) {
    return date.getUTCFullYear() + "-" +
        String(date.getUTCMonth() + 1).padStart(2, "0") + "-" +
        String(date.getUTCDate()).padStart(2, "0");
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
 * 
 * @param {Date} startDate 
 * @param {Date} endDate 
 * @returns 
 */
function getDiffInDays(startDate, endDate) {
    return (endDate.valueOf() - startDate.valueOf()) / (1000 * 60 * 60 * 24)
}
/**
 * 
 * @param {Date} date 
 * @returns 
 */
function lastDayOfMonth(date) {
    return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0));
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