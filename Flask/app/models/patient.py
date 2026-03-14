from app.extensions.sql_alchemy import db

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    patient_code = db.Column(db.String(10), unique=True, nullable=True) # Unique code for ACS linking
    agent_id = db.Column(db.String(128), db.ForeignKey('health_agents.id'), nullable=True) # Linked ACS
    
    # --- Identificação Básica ---
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    
    # --- Identificação (Complemento) ---
    cpf = db.Column(db.String(20), unique=True, nullable=True)
    rg = db.Column(db.String(20), nullable=True)
    marital_status = db.Column(db.String(50), nullable=True) # Estado Civil
    nationality = db.Column(db.String(50), nullable=True)
    education_level = db.Column(db.String(100), nullable=True)
    work_status = db.Column(db.String(100), nullable=True) # Ocupação
    has_whatsapp = db.Column(db.Boolean, default=False)
    
    # --- Cuidador / Emergência ---
    caregiver_name = db.Column(db.String(100), nullable=True)
    caregiver_phone = db.Column(db.String(20), nullable=True)
    
    # --- Endereço e Condições Ambientais ---
    cep = db.Column(db.String(20), nullable=True)
    street = db.Column(db.String(150), nullable=True)
    number = db.Column(db.String(20), nullable=True)
    neighborhood = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    reference_point = db.Column(db.String(200), nullable=True)
    zone = db.Column(db.String(20), nullable=True) # Urbana/Rural
    housing_type = db.Column(db.String(50), nullable=True) # Casa, Apt
    housing_status = db.Column(db.String(50), nullable=True) # Própria, Alugada
    num_residents = db.Column(db.Integer, nullable=True)
    has_potable_water = db.Column(db.Boolean, default=False)
    has_sanitation = db.Column(db.Boolean, default=False)
    has_garbage_collection = db.Column(db.Boolean, default=False)
    has_electricity = db.Column(db.Boolean, default=False)
    has_internet = db.Column(db.Boolean, default=False)
    
    # --- Condição Socioeconômica ---
    income = db.Column(db.String(100), nullable=True) # Renda Mensal
    income_source = db.Column(db.String(100), nullable=True)
    social_benefits = db.Column(db.String(255), nullable=True) # BPC, Bolsa Familia
    food_insecurity = db.Column(db.String(50), nullable=True) # nunca, as vezes, frequente
    financially_dependent = db.Column(db.Boolean, default=False)
    
    # --- Informações de Saúde Gerais ---
    # takes_medication = db.Column(db.Boolean, default=False)
    chronic_conditions = db.Column(db.Text, nullable=True) # List: hypertension, diabetes...
    # past_surgeries = db.Column(db.Text, nullable=True)
    # recent_hospitalizations = db.Column(db.Text, nullable=True)
    # medication_allergies = db.Column(db.Text, nullable=True)
    # medication_adherence = db.Column(db.String(50), nullable=True) # regular, irregular...
    
    # --- Saúde Física / Indicadores ---
    weight = db.Column(db.String(20), nullable=True)
    height = db.Column(db.String(20), nullable=True)
    mobility_status = db.Column(db.String(100), nullable=True) # sozinho, bengala, cadeira
    functional_capacity = db.Column(db.Text, nullable=True) # banho, cozinhar, vestir
    
    # --- Saúde Mental e Cognitiva ---
    perceived_memory = db.Column(db.String(50), nullable=True) # normal, leve esquecimento
    mental_diagnoses = db.Column(db.Text, nullable=True) # depressão, ansiedade, demência
    
    # --- Hábitos de Vida ---
    physical_activity_frequency = db.Column(db.String(50), nullable=True)
    sleep_quality = db.Column(db.String(50), nullable=True)
    alcohol_consumption = db.Column(db.String(50), nullable=True)
    smoking = db.Column(db.String(50), nullable=True)
    diet_quality = db.Column(db.String(50), nullable=True)
    
    # --- Rede de Apoio Social ---
    lives_alone = db.Column(db.Boolean, default=False)
    has_close_family = db.Column(db.Boolean, default=False)
    frequent_visits = db.Column(db.Boolean, default=False)
    community_activities = db.Column(db.Boolean, default=False)

    # ----------------------------------------

    user = db.relationship('User', backref=db.backref('patient_profile', uselist=False))
    # Relationship to agent is handled from the Agent side or implicitly

    def __repr__(self):
        return f'<Patient {self.id} Code:{self.patient_code}>'
