class ShiftPlanner {
    constructor() {
        this.currentWeek = 0;
        this.currentYear = new Date().getFullYear();
        this.people = [];
        this.machines = [];
        this.jobs = [];
        this.templates = [];
        this.schedule = [];
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.updateWeekDisplay();
        this.renderTimeline();
    }
    
    setupEventListeners() {
        document.getElementById('prev-week').addEventListener('click', () => this.changeWeek(-1));
        document.getElementById('next-week').addEventListener('click', () => this.changeWeek(1));
        document.getElementById('generate-schedule').addEventListener('click', () => this.generateSchedule());
        document.getElementById('export-schedule').addEventListener('click', () => this.exportSchedule());
        
        document.getElementById('add-person-btn').addEventListener('click', () => this.showPersonModal());
        document.getElementById('add-machine-btn').addEventListener('click', () => this.showMachineModal());
        document.getElementById('add-job-btn').addEventListener('click', () => this.showJobModal());
        document.getElementById('add-template-btn').addEventListener('click', () => this.showTemplateModal());
        
        document.getElementById('mark-absence').addEventListener('click', () => this.markAbsence());
        
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal-overlay').classList.remove('active');
            });
        });
        
        document.getElementById('progress-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateJobProgress();
        });
    }
    
    async loadInitialData() {
        try {
            const [people, machines, jobs, templates] = await Promise.all([
                this.fetchData('/api/people'),
                this.fetchData('/api/machines'),
                this.fetchData('/api/jobs'),
                this.fetchData('/api/job_templates')
            ]);
            
            this.people = people;
            this.machines = machines;
            this.jobs = jobs;
            this.templates = templates;
            
            this.renderPeople();
            this.renderMachines();
            this.renderJobs();
            this.renderTemplates();
            this.loadSchedule();
            this.updatePersonSelect();
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }
    
    async fetchData(url) {
        const response = await fetch(url);
        return response.json();
    }
    
    getWeekDates() {
        const start = new Date(this.currentYear, 0, 1);
        const daysToMonday = (start.getDay() === 0 ? -6 : 1) - start.getDay();
        start.setDate(start.getDate() + daysToMonday + (this.currentWeek * 7));
        
        const dates = [];
        for (let i = 0; i < 5; i++) {
            const date = new Date(start);
            date.setDate(start.getDate() + i);
            dates.push(date);
        }
        return dates;
    }
    
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    updateWeekDisplay() {
        const dates = this.getWeekDates();
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const weekNum = this.currentWeek + 1;
        const month = monthNames[dates[0].getMonth()];
        document.getElementById('current-week').textContent = `Week ${weekNum} - ${month} ${this.currentYear}`;
    }
    
    changeWeek(delta) {
        this.currentWeek += delta;
        if (this.currentWeek < 0) {
            this.currentWeek = 51;
            this.currentYear--;
        } else if (this.currentWeek > 51) {
            this.currentWeek = 0;
            this.currentYear++;
        }
        this.updateWeekDisplay();
        this.renderTimeline();
        this.loadSchedule();
    }
    
    renderTimeline() {
        const dates = this.getWeekDates();
        const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
        
        const daysHeader = document.getElementById('days-header');
        daysHeader.innerHTML = dates.map((date, i) => `
            <div class="day-column">
                ${dayNames[i]}<br>
                <small>${date.getDate()}/${date.getMonth() + 1}</small>
            </div>
        `).join('');
        
        const timelineBody = document.getElementById('timeline-body');
        timelineBody.innerHTML = this.machines.map(machine => `
            <div class="machine-row" data-machine-id="${machine.id}">
                <div class="machine-name">${machine.name}</div>
                <div class="machine-schedule">
                    ${dates.map(date => `
                        <div class="day-slot" data-date="${this.formatDate(date)}" data-machine="${machine.id}">
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }
    
    async loadSchedule() {
        const dates = this.getWeekDates();
        const startDate = this.formatDate(dates[0]);
        const endDate = this.formatDate(dates[4]);
        
        try {
            const response = await fetch(`/api/schedule?start_date=${startDate}&end_date=${endDate}`);
            this.schedule = await response.json();
            this.renderSchedule();
        } catch (error) {
            console.error('Error loading schedule:', error);
        }
    }
    
    renderSchedule() {
        document.querySelectorAll('.day-slot').forEach(slot => {
            slot.innerHTML = '';
        });
        
        this.schedule.forEach(assignment => {
            const slot = document.querySelector(
                `.day-slot[data-date="${assignment.date}"][data-machine="${assignment.machine_id}"]`
            );
            
            if (slot) {
                const person = this.people.find(p => p.id === assignment.person_id);
                const skillLevel = person && person.skills ? 
                    (person.skills[assignment.machine_name] || 1) : 1;
                
                const job = this.jobs.find(j => j.id === assignment.job_id);
                const isHighPriority = job && job.priority > 0;
                
                const assignmentBox = document.createElement('div');
                assignmentBox.className = `assignment-box skill-${skillLevel} ${isHighPriority ? 'high-priority' : ''}`;
                assignmentBox.innerHTML = `
                    <div class="person-name">${assignment.person_name}</div>
                    <div class="job-name">${assignment.job_name || 'No job'}</div>
                `;
                
                assignmentBox.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    this.showProgressModal(assignment);
                });
                
                slot.appendChild(assignmentBox);
            }
        });
    }
    
    renderPeople() {
        const container = document.getElementById('people-list');
        container.innerHTML = this.people.map(person => {
            const skills = Object.entries(person.skills || {})
                .map(([machine, level]) => `${machine}:${level}`)
                .join(', ');
            
            return `
                <div class="list-item">
                    <div class="list-item-info">
                        <div class="list-item-name">${person.name}</div>
                        <div class="list-item-details">Skills: ${skills || 'None'}</div>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn-icon btn-edit" onclick="app.editPerson(${person.id})">✏</button>
                        <button class="btn-icon btn-delete" onclick="app.deletePerson(${person.id})">×</button>
                    </div>
                </div>
            `;
        }).join('') || '<div class="empty-state">No people added yet</div>';
    }
    
    renderMachines() {
        const container = document.getElementById('machine-list');
        container.innerHTML = this.machines.map(machine => `
            <div class="list-item">
                <div class="list-item-info">
                    <div class="list-item-name">${machine.name}</div>
                    <div class="list-item-details">
                        Max operators: ${machine.max_operators}, 
                        Throughput: ${machine.base_throughput}/hr
                    </div>
                </div>
                <div class="list-item-actions">
                    <button class="btn-icon btn-delete" onclick="app.deleteMachine(${machine.id})">×</button>
                </div>
            </div>
        `).join('') || '<div class="empty-state">No machines added yet</div>';
    }
    
    renderJobs() {
        const container = document.getElementById('job-list');
        container.innerHTML = this.jobs.map(job => {
            const priorityClass = job.priority > 0 ? 'priority-high' : 'priority-normal';
            const statusClass = `status-${job.status}`;
            const progress = job.quantity > 0 ? 
                Math.round((job.completed_quantity / job.quantity) * 100) : 0;
            
            return `
                <div class="list-item">
                    <div class="list-item-info">
                        <div class="list-item-name">
                            <span class="status-indicator ${statusClass}"></span>
                            ${job.project_name}
                        </div>
                        <div class="list-item-details">
                            Due: ${job.due_date || 'Not set'}<br>
                            Progress: ${job.completed_quantity}/${job.quantity} (${progress}%)<br>
                            <span class="priority-indicator ${priorityClass}">
                                ${job.priority > 0 ? 'HIGH' : 'Normal'}
                            </span>
                            ${job.precision_required ? '<span class="priority-indicator">Precision</span>' : ''}
                        </div>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn-icon btn-delete" onclick="app.deleteJob(${job.id})">×</button>
                    </div>
                </div>
            `;
        }).join('') || '<div class="empty-state">No jobs in queue</div>';
    }
    
    renderTemplates() {
        const container = document.getElementById('template-list');
        container.innerHTML = this.templates.map(template => `
            <div class="list-item">
                <div class="list-item-info">
                    <div class="list-item-name">#${template.code} - ${template.name}</div>
                    <div class="list-item-details">
                        Machines: ${template.machine_sequence}<br>
                        Est. hours: ${template.estimated_hours}
                        ${template.precision_required ? ' (Precision)' : ''}
                    </div>
                </div>
            </div>
        `).join('') || '<div class="empty-state">No templates created yet</div>';
    }
    
    updatePersonSelect() {
        const select = document.getElementById('person-select');
        select.innerHTML = '<option value="">Select Person</option>' +
            this.people.map(person => 
                `<option value="${person.id}">${person.name}</option>`
            ).join('');
    }
    
    showPersonModal() {
        const modal = document.getElementById('modal-overlay');
        document.getElementById('modal-title').textContent = 'Add Person';
        
        const machineSkills = this.machines.map(machine => `
            <div class="skill-input">
                <label>${machine.name}</label>
                <select name="skill_${machine.name}">
                    <option value="0">None</option>
                    <option value="1">Level 1</option>
                    <option value="2">Level 2</option>
                    <option value="3">Level 3</option>
                    <option value="4">Level 4</option>
                    <option value="5">Level 5</option>
                </select>
            </div>
        `).join('');
        
        document.getElementById('modal-body').innerHTML = `
            <form id="person-form">
                <div class="form-group">
                    <label for="person-name">Name:</label>
                    <input type="text" id="person-name" required>
                </div>
                <div class="form-group">
                    <label>Machine Skills:</label>
                    <div class="skills-grid">
                        ${machineSkills}
                    </div>
                </div>
                <button type="submit" class="btn-primary">Add Person</button>
            </form>
        `;
        
        document.getElementById('person-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addPerson();
        });
        
        modal.classList.add('active');
    }
    
    showMachineModal() {
        const modal = document.getElementById('modal-overlay');
        document.getElementById('modal-title').textContent = 'Add Machine';
        
        document.getElementById('modal-body').innerHTML = `
            <form id="machine-form">
                <div class="form-group">
                    <label for="machine-name">Machine Name:</label>
                    <input type="text" id="machine-name" required>
                </div>
                <div class="form-group">
                    <label for="max-operators">Max Operators:</label>
                    <input type="number" id="max-operators" min="1" value="1" required>
                </div>
                <div class="form-group">
                    <label for="base-throughput">Base Throughput (items/hr):</label>
                    <input type="number" id="base-throughput" min="1" value="100" required>
                </div>
                <button type="submit" class="btn-primary">Add Machine</button>
            </form>
        `;
        
        document.getElementById('machine-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addMachine();
        });
        
        modal.classList.add('active');
    }
    
    showJobModal() {
        const modal = document.getElementById('modal-overlay');
        document.getElementById('modal-title').textContent = 'Add Job';
        
        const templateOptions = this.templates.map(t => 
            `<option value="${t.id}">#${t.code} - ${t.name}</option>`
        ).join('');
        
        const machineOptions = this.machines.map(m => 
            `<option value="${m.name}">${m.name}</option>`
        ).join('');
        
        document.getElementById('modal-body').innerHTML = `
            <form id="job-form">
                <div class="form-group">
                    <label for="job-name">Project Name:</label>
                    <input type="text" id="job-name" required>
                </div>
                <div class="form-group">
                    <label for="job-template">Template (optional):</label>
                    <select id="job-template">
                        <option value="">Custom Job</option>
                        ${templateOptions}
                    </select>
                </div>
                <div class="form-group">
                    <label for="job-quantity">Quantity:</label>
                    <input type="number" id="job-quantity" min="1" required>
                </div>
                <div class="form-group">
                    <label for="job-due-date">Due Date:</label>
                    <input type="date" id="job-due-date" required>
                </div>
                <div class="form-group">
                    <label for="job-machines">Machine Sequence (comma-separated):</label>
                    <input type="text" id="job-machines" placeholder="e.g., Machine A, Machine B">
                </div>
                <div class="form-group">
                    <label for="job-hours">Estimated Hours:</label>
                    <input type="number" id="job-hours" min="0.5" step="0.5" value="8">
                </div>
                <div class="form-group checkbox-group">
                    <input type="checkbox" id="job-priority">
                    <label for="job-priority">High Priority</label>
                </div>
                <div class="form-group checkbox-group">
                    <input type="checkbox" id="job-precision">
                    <label for="job-precision">Precision Required</label>
                </div>
                <button type="submit" class="btn-primary">Add Job</button>
            </form>
        `;
        
        document.getElementById('job-template').addEventListener('change', (e) => {
            if (e.target.value) {
                const template = this.templates.find(t => t.id == e.target.value);
                if (template) {
                    document.getElementById('job-machines').value = template.machine_sequence;
                    document.getElementById('job-hours').value = template.estimated_hours;
                    document.getElementById('job-precision').checked = template.precision_required;
                }
            }
        });
        
        document.getElementById('job-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addJob();
        });
        
        modal.classList.add('active');
    }
    
    showTemplateModal() {
        const modal = document.getElementById('modal-overlay');
        document.getElementById('modal-title').textContent = 'Add Job Template';
        
        document.getElementById('modal-body').innerHTML = `
            <form id="template-form">
                <div class="form-group">
                    <label for="template-code">Template Code:</label>
                    <input type="text" id="template-code" placeholder="e.g., 101" required>
                </div>
                <div class="form-group">
                    <label for="template-name">Template Name:</label>
                    <input type="text" id="template-name" required>
                </div>
                <div class="form-group">
                    <label for="template-machines">Machine Sequence:</label>
                    <input type="text" id="template-machines" placeholder="e.g., Machine A, Machine B" required>
                </div>
                <div class="form-group">
                    <label for="template-hours">Estimated Hours:</label>
                    <input type="number" id="template-hours" min="0.5" step="0.5" required>
                </div>
                <div class="form-group checkbox-group">
                    <input type="checkbox" id="template-precision">
                    <label for="template-precision">Precision Required</label>
                </div>
                <button type="submit" class="btn-primary">Add Template</button>
            </form>
        `;
        
        document.getElementById('template-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addTemplate();
        });
        
        modal.classList.add('active');
    }
    
    showProgressModal(assignment) {
        const modal = document.getElementById('job-progress-modal');
        document.getElementById('progress-job-name').textContent = assignment.job_name;
        document.getElementById('progress-machine-name').textContent = assignment.machine_name;
        
        modal.dataset.jobId = assignment.job_id;
        modal.dataset.machineId = assignment.machine_id;
        modal.dataset.date = assignment.date;
        
        const job = this.jobs.find(j => j.id === assignment.job_id);
        if (job) {
            document.getElementById('completed-quantity').value = job.completed_quantity;
            document.getElementById('completed-quantity').max = job.quantity;
        }
        
        modal.classList.add('active');
    }
    
    async addPerson() {
        const name = document.getElementById('person-name').value;
        const skills = {};
        
        this.machines.forEach(machine => {
            const select = document.querySelector(`select[name="skill_${machine.name}"]`);
            if (select && select.value !== '0') {
                skills[machine.name] = parseInt(select.value);
            }
        });
        
        try {
            const response = await fetch('/api/people', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, skills })
            });
            
            if (response.ok) {
                document.getElementById('modal-overlay').classList.remove('active');
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error adding person:', error);
        }
    }
    
    async addMachine() {
        const data = {
            name: document.getElementById('machine-name').value,
            max_operators: parseInt(document.getElementById('max-operators').value),
            base_throughput: parseFloat(document.getElementById('base-throughput').value)
        };
        
        try {
            const response = await fetch('/api/machines', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                document.getElementById('modal-overlay').classList.remove('active');
                await this.loadInitialData();
                this.renderTimeline();
            }
        } catch (error) {
            console.error('Error adding machine:', error);
        }
    }
    
    async addJob() {
        const data = {
            project_name: document.getElementById('job-name').value,
            template_id: document.getElementById('job-template').value || null,
            quantity: parseInt(document.getElementById('job-quantity').value),
            due_date: document.getElementById('job-due-date').value,
            machine_sequence: document.getElementById('job-machines').value,
            estimated_hours: parseFloat(document.getElementById('job-hours').value),
            priority: document.getElementById('job-priority').checked ? 1 : 0,
            precision_required: document.getElementById('job-precision').checked
        };
        
        try {
            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                document.getElementById('modal-overlay').classList.remove('active');
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error adding job:', error);
        }
    }
    
    async addTemplate() {
        const data = {
            code: document.getElementById('template-code').value,
            name: document.getElementById('template-name').value,
            machine_sequence: document.getElementById('template-machines').value,
            estimated_hours: parseFloat(document.getElementById('template-hours').value),
            precision_required: document.getElementById('template-precision').checked
        };
        
        try {
            const response = await fetch('/api/job_templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                document.getElementById('modal-overlay').classList.remove('active');
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error adding template:', error);
        }
    }
    
    async deletePerson(id) {
        if (!confirm('Are you sure you want to delete this person?')) return;
        
        try {
            const response = await fetch('/api/people', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            
            if (response.ok) {
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error deleting person:', error);
        }
    }
    
    async deleteMachine(id) {
        if (!confirm('Are you sure you want to delete this machine?')) return;
        
        try {
            const response = await fetch('/api/machines', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            
            if (response.ok) {
                await this.loadInitialData();
                this.renderTimeline();
            }
        } catch (error) {
            console.error('Error deleting machine:', error);
        }
    }
    
    async deleteJob(id) {
        if (!confirm('Are you sure you want to delete this job?')) return;
        
        try {
            const response = await fetch('/api/jobs', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            
            if (response.ok) {
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error deleting job:', error);
        }
    }
    
    async markAbsence() {
        const personId = document.getElementById('person-select').value;
        const date = document.getElementById('absence-date').value;
        const reason = document.getElementById('absence-reason').value || 'Vacation';
        
        if (!personId || !date) {
            alert('Please select a person and date');
            return;
        }
        
        try {
            const response = await fetch('/api/availability', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    person_id: parseInt(personId),
                    date,
                    available: 0,
                    reason
                })
            });
            
            if (response.ok) {
                document.getElementById('absence-date').value = '';
                document.getElementById('absence-reason').value = '';
                this.loadAbsences();
            }
        } catch (error) {
            console.error('Error marking absence:', error);
        }
    }
    
    async loadAbsences() {
        const dates = this.getWeekDates();
        const startDate = this.formatDate(dates[0]);
        const endDate = this.formatDate(dates[4]);
        
        try {
            const response = await fetch(`/api/availability?start_date=${startDate}&end_date=${endDate}`);
            const absences = await response.json();
            
            const container = document.getElementById('absence-list');
            container.innerHTML = absences.map(absence => `
                <div class="absence-item">
                    ${absence.person_name} - ${absence.date}<br>
                    <small>${absence.reason}</small>
                </div>
            `).join('') || '<div>No absences this week</div>';
        } catch (error) {
            console.error('Error loading absences:', error);
        }
    }
    
    async generateSchedule() {
        const dates = this.getWeekDates();
        const startDate = this.formatDate(dates[0]);
        const endDate = this.formatDate(dates[4]);
        
        const btn = document.getElementById('generate-schedule');
        btn.innerHTML = '<span class="loading"></span> Generating...';
        btn.disabled = true;
        
        try {
            const response = await fetch('/api/generate_schedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_date: startDate, end_date: endDate })
            });
            
            if (response.ok) {
                await this.loadSchedule();
            }
        } catch (error) {
            console.error('Error generating schedule:', error);
        } finally {
            btn.innerHTML = 'Generate Schedule';
            btn.disabled = false;
        }
    }
    
    async updateJobProgress() {
        const modal = document.getElementById('job-progress-modal');
        const data = {
            job_id: parseInt(modal.dataset.jobId),
            machine_id: parseInt(modal.dataset.machineId),
            date: modal.dataset.date,
            completed_quantity: parseInt(document.getElementById('completed-quantity').value),
            remaining_hours: parseFloat(document.getElementById('remaining-hours').value) || 0
        };
        
        try {
            const response = await fetch('/api/update_progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                modal.classList.remove('active');
                await this.loadInitialData();
            }
        } catch (error) {
            console.error('Error updating progress:', error);
        }
    }
    
    exportSchedule() {
        const dates = this.getWeekDates();
        const startDate = this.formatDate(dates[0]);
        const endDate = this.formatDate(dates[4]);
        
        window.location.href = `/api/export_schedule?start_date=${startDate}&end_date=${endDate}`;
    }
}

const app = new ShiftPlanner();