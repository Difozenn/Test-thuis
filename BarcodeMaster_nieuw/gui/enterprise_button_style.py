"""
Enterprise-grade button styling for BarcodeMaster
Professional color palette and design system
"""

# Enterprise Color System (based on Microsoft Fluent Design)
COLORS = {
    # Primary Actions
    'primary': '#0078D4',           # Microsoft Blue
    'primary_hover': '#106EBE',     # Darker blue on hover
    'primary_disabled': '#B3D9F2',  # Light blue when disabled
    
    # Destructive Actions  
    'danger': '#DC3545',            # Bootstrap Danger Red
    'danger_hover': '#C82333',      # Darker red on hover
    
    # Success/Positive Actions
    'success': '#28A745',           # Bootstrap Success Green  
    'success_hover': '#218838',     # Darker green on hover
    
    # Secondary/Neutral Actions
    'secondary': '#6C757D',         # Bootstrap Secondary Gray
    'secondary_hover': '#5A6268',   # Darker gray on hover
    
    # Warning/Caution Actions
    'warning': '#FFC107',           # Bootstrap Warning Yellow
    'warning_hover': '#E0A800',     # Darker yellow on hover
    
    # Text Colors
    'text_primary': '#212529',      # Main text
    'text_secondary': '#6C757D',    # Secondary text
    'text_muted': '#ADB5BD',        # Muted text
    'text_white': '#FFFFFF',        # White text
    
    # Background Colors
    'bg_primary': '#FFFFFF',        # Main background
    'bg_secondary': '#F8F9FA',      # Secondary background
    'bg_tertiary': '#E9ECEF',       # Tertiary background
    
    # Border Colors
    'border_light': '#DEE2E6',      # Light border
    'border_medium': '#CED4DA',     # Medium border
    'border_dark': '#ADB5BD',       # Dark border
}

# Button Style Configuration
BUTTON_STYLES = {
    'start': {
        'normal': {
            'bg': COLORS['primary'],
            'fg': COLORS['text_white'],
            'text': 'Start Sessie'
        },
        'active': {
            'bg': COLORS['danger'],
            'fg': COLORS['text_white'],
            'text': 'Stop Sessie'
        }
    },
    'pause': {
        'normal': {
            'bg': COLORS['secondary'],
            'fg': COLORS['text_white'],
            'text': 'Pauzeer'
        },
        'paused': {
            'bg': COLORS['success'],
            'fg': COLORS['text_white'],
            'text': 'Hervat'
        }
    },
    'batch': {
        'normal': {
            'bg': COLORS['primary'],
            'fg': COLORS['text_white'],
            'text': 'Nieuwe Batch'
        },
        'background': {
            'bg': COLORS['secondary'],
            'fg': COLORS['text_white'],
            'text': 'Stop Achtergrond'
        }
    }
}

# Typography
FONTS = {
    'button': ('Segoe UI', 10),
    'label': ('Segoe UI', 10),
    'heading': ('Segoe UI', 11, 'bold'),
    'small': ('Segoe UI', 9),
    'status': ('Segoe UI', 10)
}

# Layout Constants
PADDING = {
    'button_x': 20,
    'button_y': 10,
    'frame': 15,
    'spacing': 5
}