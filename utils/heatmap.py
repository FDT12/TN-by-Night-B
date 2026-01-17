# backend/utils/heatmap.py
"""
Utility functions for heatmap data processing
"""

# All 24 Tunisian governorates (states)
TUNISIAN_GOVERNORATES = [
    'Ariana', 'Béja', 'Ben Arous', 'Bizerte', 'Gabès', 'Gafsa',
    'Jendouba', 'Kairouan', 'Kasserine', 'Kebili', 'Kef', 'Mahdia',
    'Manouba', 'Medenine', 'Monastir', 'Nabeul', 'Sfax', 'Sidi Bouzid',
    'Siliana', 'Sousse', 'Tataouine', 'Tozeur', 'Tunis', 'Zaghouan'
]

# City to Governorate mapping (for cities that belong to governorates)
CITY_TO_GOVERNORATE = {
    'Tunis': 'Tunis',
    'Ariana': 'Ariana',
    'Ben Arous': 'Ben Arous',
    'Manouba': 'Manouba',
    'Nabeul': 'Nabeul',
    'Zaghouan': 'Zaghouan',
    'Bizerte': 'Bizerte',
    'Béja': 'Béja',
    'Jendouba': 'Jendouba',
    'Kef': 'Kef',
    'Siliana': 'Siliana',
    'Sousse': 'Sousse',
    'Monastir': 'Monastir',
    'Mahdia': 'Mahdia',
    'Sfax': 'Sfax',
    'Kairouan': 'Kairouan',
    'Kasserine': 'Kasserine',
    'Sidi Bouzid': 'Sidi Bouzid',
    'Gabès': 'Gabès',
    'Medenine': 'Medenine',
    'Tataouine': 'Tataouine',
    'Gafsa': 'Gafsa',
    'Tozeur': 'Tozeur',
    'Kebili': 'Kebili',
}


def get_color_for_score(score):
    """
    Get color based on event score:
    - 0 events: blue (#0066CC or #3388FF)
    - 1-3 events: yellow (#FFCC00 or #FFD700)
    - 4-6 events: orange (#FF6600 or #FF8800)
    - 7+ events: red (#CC0000 or #FF0000)
    """
    if score == 0:
        return '#3388FF'  # Blue
    elif 1 <= score <= 3:
        return '#FFD700'  # Yellow/Gold
    elif 4 <= score <= 6:
        return '#FF8800'  # Orange
    else:  # score >= 7
        return '#FF0000'  # Red


def calculate_governorate_scores(events):
    """
    Calculate event count per governorate from events list
    
    Args:
        events: List of event dictionaries with 'city' field
        
    Returns:
        Dictionary mapping governorate names to event counts
    """
    scores = {gov: 0 for gov in TUNISIAN_GOVERNORATES}
    
    for event in events:
        city = event.get('city', '').strip()
        if not city or city in ['Unknown', 'Error', 'Pending']:
            continue
            
        # Normalize city name to governorate
        governorate = CITY_TO_GOVERNORATE.get(city, city)
        
        # If city is already a governorate name, use it directly
        if governorate in scores:
            scores[governorate] += 1
        elif city in scores:
            scores[city] += 1
    
    return scores


def get_heatmap_data(events):
    """
    Generate heatmap data structure for frontend with event details
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Dictionary with governorate data including scores, colors, and event lists
    """
    # Initialize data structure
    heatmap_data = {
        gov: {
            'score': 0, 
            'color': get_color_for_score(0), 
            'events_count': 0,
            'events': []
        } 
        for gov in TUNISIAN_GOVERNORATES
    }
    
    for event in events:
        city = event.get('city', '').strip()
        if not city or city in ['Unknown', 'Error', 'Pending']:
            continue
            
        # Normalize city name to governorate
        governorate = CITY_TO_GOVERNORATE.get(city, city)
        
        # If matches a known governorate
        target_gov = None
        if governorate in heatmap_data:
            target_gov = governorate
        elif city in heatmap_data:
            target_gov = city
            
        if target_gov:
            data = heatmap_data[target_gov]
            data['events_count'] += 1
            data['score'] += 1
            data['color'] = get_color_for_score(data['score'])
            
            # Add up to 5 events
            if len(data['events']) < 5:
                data['events'].append(event)
    
    return heatmap_data


def get_heatmap_summary(events):
    """
    Get summary statistics for heatmap
    
    Returns:
        Dictionary with total events, active governorates, etc.
    """
    scores = calculate_governorate_scores(events)
    total_events = sum(scores.values())
    active_governorates = sum(1 for score in scores.values() if score > 0)
    
    return {
        'total_events': total_events,
        'active_governorates': active_governorates,
        'total_governorates': len(TUNISIAN_GOVERNORATES),
        'governorates_with_events': [gov for gov, score in scores.items() if score > 0]
    }
