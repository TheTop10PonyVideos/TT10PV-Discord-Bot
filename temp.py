def is_valid_wl_candidate(video_data):
    return (
        not video_data['searchable'] # Already seachable
        and not any( # Clearly ineligible votes are not valid candidates
            annotation['trigger'] in ('Littleshy video', '<30 second video', 'Video too old')
            for annotation in video_data['annotations']
        )
    )
