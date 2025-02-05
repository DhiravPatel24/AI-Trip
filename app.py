
import streamlit as st
import pandas as pd
from groq_service import TripPlannerService
import folium
from geopy.distance import geodesic
import json
import os
from datetime import datetime

trip_planner_service = TripPlannerService()

SAVED_TRIPS_DIR = "saved_trips"
os.makedirs(SAVED_TRIPS_DIR, exist_ok=True)

st.set_page_config(page_title="Trip Planner", page_icon="✈️", layout="centered")
st.title("✈️ AI Trip Planner")
st.caption("Plan your perfect getaway effortlessly.")

def save_trip_data(data):
    """Save trip data to JSON file"""
    filename = f"{data['destination']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    filepath = os.path.join(SAVED_TRIPS_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f)
    return filepath

def load_trip_data(filepath):
    """Load trip data from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_saved_trips():
    """Get list of saved trip files"""
    return [f for f in os.listdir(SAVED_TRIPS_DIR) if f.endswith('.json')]

def display_trip(trip_data):
    """Display trip data from loaded JSON"""
    # Display basic info
    st.markdown(f"### ✨ Itinerary for {trip_data['destination']} ✨")
    st.markdown(f"**Duration**: {trip_data['trip_duration']} days")
    st.markdown(f"**Activities**: {', '.join(trip_data['activities'])}")
    
    # Display travel instructions
    if 'travel_instructions' in trip_data:
        st.markdown("### ✈️ Travel Instructions")
        ti = trip_data['travel_instructions']
        st.markdown(f"**Mode of Transportation**: {ti.get('mode_of_transportation', 'N/A')}")
        st.markdown(f"**Estimated Travel Time**: {ti.get('estimated_travel_time', 'N/A')}")
        st.markdown(f"**Estimated Distance**: {ti.get('estimated_distance', 'N/A')}")
        st.markdown(f"**Route Details**: {ti.get('route_details', 'N/A')}")
    
    # Display train schedule if available
    if 'train_schedule' in trip_data and trip_data['train_schedule']:
        st.markdown("### 🚂 Train Schedule")
        df = pd.DataFrame(trip_data['train_schedule'])
        
        # Format DataFrame columns
        df['Departure'] = df['departure'].apply(lambda x: f"{x['time']} ({x['station']})")
        df['Arrival'] = df['arrival'].apply(lambda x: f"{x['time']} ({x['station']})")
        df['Duration'] = df['duration']
        
        st.dataframe(
            df[['name', 'number', 'Departure', 'Arrival', 'Duration', 'runs_on']]
            .rename(columns={
                'name': 'Train Name',
                'number': 'Train Number',
                'runs_on': 'Running Days'
            }),
            height=400,
            use_container_width=True
        )
    
    # Display itinerary
    st.markdown("### 🗺️ Daily Itinerary")
    if 'itinerary' in trip_data and 'daily_activities' in trip_data['itinerary']:
        for idx, day_activities in enumerate(trip_data['itinerary']['daily_activities'], start=1):
            st.markdown(f"#### Day {idx}:")
            for activity in day_activities:
                st.markdown(f"- **{activity}**")
    else:
        st.error("Daily activities data is missing or invalid.")
    
    # Display map
    if 'coordinates' in trip_data and 'coordinates1' in trip_data:
        dest_1 = trip_data['coordinates1']
        dest_2 = trip_data['coordinates']
        if dest_1 and dest_2:
            try:
                distance = geodesic(dest_1, dest_2).km
                map_center = [(dest_1[0] + dest_2[0])/2, (dest_1[1] + dest_2[1])/2]
                m = folium.Map(location=map_center, zoom_start=8)
                folium.Marker(dest_1, popup='Starting Point').add_to(m)
                folium.Marker(dest_2, popup='Destination').add_to(m)
                folium.PolyLine([dest_1, dest_2], color="green").add_to(m)
                st.markdown(f"### 📍 Map View (Distance: {distance:.2f} km)")
                st.components.v1.html(m._repr_html_(), width=700, height=500)
            except Exception as e:
                st.error(f"Error displaying map: {e}")
    
    # Display images
    if 'images' in trip_data and trip_data['images']:
        st.markdown("### 🖼️ Destination Images")
        cols = st.columns(3)
        for idx, img_url in enumerate(trip_data['images'][:6]):
            cols[idx % 3].image(img_url)

with st.sidebar:
    st.header("Trip Customization 📝")
    
    # Load existing trips
    saved_trips = get_saved_trips()
    selected_trip = st.selectbox("Load Saved Trip", [""] + saved_trips)
    
    if selected_trip:
        trip_data = load_trip_data(os.path.join(SAVED_TRIPS_DIR, selected_trip))
        st.session_state.trip_data = trip_data
    else:
        st.session_state.trip_data = None
    
    # New trip inputs
    st.divider()
    st.subheader("Plan New Trip")
    destination = st.text_input("Destination", placeholder="e.g., Udaipur, Kashmir")
    trip_duration = st.slider("Trip Duration (days)", 1, 15, 5)
    activities = st.multiselect(
        "Preferred Activities", 
        options=["Sightseeing", "Dining", "Hiking", "Shopping", "Museums", "Nightlife", "Adventure Sports","All possible"], 
        default=[]
    )
    generate_button = st.button("Generate Itinerary 😼")

if st.session_state.trip_data:
    display_trip(st.session_state.trip_data)
elif generate_button:
    if destination and activities:
        with st.spinner("Generating your perfect itinerary..."):
            try:
                # Generate trip components
                itinerary = trip_planner_service.generate_itinerary(destination, trip_duration, activities)
                travel_instructions = trip_planner_service.get_travel_instructions("Ahmedabad", destination)
                destination_info = trip_planner_service.scrape_destination_info(destination)
                
                # Error handling for invalid itinerary
                if not itinerary or "daily_activities" not in itinerary:
                    st.error("Error generating itinerary: Invalid data format")
                    st.stop()
                
                # Add train schedule if transportation is by train
                train_schedule = None
                mode_of_transportation = travel_instructions.get('mode_of_transportation', '').lower()
                
                # Check if train should be included based on user selection or instructions
                if 'train' in mode_of_transportation or 'flight' in mode_of_transportation:
                    train_schedule = trip_planner_service.scrape_train_schedule(
                        "Ahmedabad",
                        destination
                    )
                
                # Package trip data
                trip_data = {
                    "destination": destination,
                    "trip_duration": trip_duration,
                    "activities": activities,
                    "itinerary": itinerary,
                    "travel_instructions": travel_instructions,
                    "coordinates": destination_info.get("coordinates"),
                    "coordinates1": destination_info.get("coordinates1"),
                    "images": destination_info.get("images", []),
                    "train_schedule": train_schedule,
                    "generated_at": datetime.now().isoformat()
                }
                
                # Save and display
                save_path = save_trip_data(trip_data)
                st.success("Trip plan generated successfully!")
                display_trip(trip_data)
                
            except Exception as e:
                st.error(f"Error generating trip: {str(e)}")
    else:
        st.warning("Please provide both destination and activities!")
else:
    st.markdown("""
        ### Welcome to AI Trip Planner! 🌟
        - **Load existing trips** from the sidebar
        - Create **new trips** using the sidebar controls
        - All trips are automatically saved for future reference
        
        **Features:**
        - 🗺️ Interactive maps with distance calculations
        - 🖼️ Destination images gallery
        - ✈️ Travel instructions between cities
        - 🚂 Train schedule integration
        - 💾 Automatic saving of all planned trips
    """)
