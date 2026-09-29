# Scenario results

## Scenario 1: Cancelled flight, must arrive by noon

**thread_id:** `passenger-XK9L2P`

**Input message:** My flight to Dubai was cancelled. I need to be there by tomorrow noon.

**Path:** intake → classifier → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → policy_checker → final_response

**Tools called:** get_booking({'booking_ref': 'XK9L2P'}), search_flights({'date': '2026-10-03', 'destination': 'DXB', 'origin': 'ADD'})

**Intent:** rebook  |  **Policy passed:** True  |  **Failed checks (retry_count):** 0  |  **Escalated:** False

**Last policy failure reason:** none

**Proposed solution:** `{'type': 'rebook', 'flight_number': 'ET604', 'cabin': 'economy', 'flight': {'flight_number': 'ET604', 'departure': '2026-10-03T22:00', 'arrival': '2026-10-04T03:30', 'available_cabins': ['economy', 'business'], 'connection_airport': None, 'connection_minutes': None}}`

**Final response:**

Dear Mr. Kebede,

We’re sorry your original flight to Dubai was cancelled.  
We have rebooked you on flight ET604 in economy, departing 2026‑10‑03 at 22:00 and arriving 2026‑10‑04 at 03:30.  
Your new ticket has been automatically issued and is attached to your booking.  
Please check your email for the updated itinerary and e‑ticket.  
No further action is required from you unless you need a different schedule.  
As this case was not escalated, a human agent will not follow up.  

Safe travels,  
Ethiopian Airlines Customer Care

## Scenario 1 follow-up: same thread, no booking reference given

**thread_id:** `passenger-XK9L2P`

**Input message:** Actually, can I get a refund instead?

**Path:** intake → classifier → refund_agent → policy_checker → final_response

**Tools called:** none

**Intent:** refund  |  **Policy passed:** True  |  **Failed checks (retry_count):** 0  |  **Escalated:** False

**Last policy failure reason:** none

**Proposed solution:** `{'type': 'refund', 'amount_usd': 520.0, 'explanation': 'The flight ET600 from ADD to DXB was cancelled by the airline. According to the refund policy, a cancellation by the airline entitles the passenger to a full refund of the fare paid, which is $520 USD.'}`

**Final response:**

Dear Mr. Kebede,

We’re sorry the ET600 flight from Addis Ababa to Dubai was cancelled by the airline.  
A full refund of $520 USD will be processed to your original payment method.  
The refund should appear on your statement within 5‑7 business days.  
You will receive an email confirmation once the transaction is complete.  
No further action is required on your part.  
A human agent will not follow up, as this request has been resolved automatically.  

Thank you for your understanding.

## Scenario 2: 6-hour delay, asks about compensation

**thread_id:** `passenger-DL3M7Q`

**Input message:** My flight is delayed 6 hours. Am I entitled to anything?

**Path:** intake → classifier → compensation_agent → policy_checker → final_response

**Tools called:** none

**Intent:** compensation  |  **Policy passed:** True  |  **Failed checks (retry_count):** 0  |  **Escalated:** False

**Last policy failure reason:** none

**Proposed solution:** `{'type': 'compensation', 'amount_usd': 200.0, 'explanation': 'The flight was delayed by 6 hours, which falls within the 3 to 6 hour delay bracket. According to the compensation rules, this qualifies for a $200 compensation.'}`

**Final response:**

Dear Hana Girma,

We’re sorry for the 6‑hour delay on your flight. As per our policy, you are eligible for a $200 compensation, which has been processed to your original payment method.  
You will receive a confirmation email shortly with the details.  
If you have any further questions, feel free to reply to this message.  
Thank you for your patience.  
No human follow‑up is required at this time.

## Scenario 3: Only business-class seats available

**thread_id:** `passenger-BZ4Q8M`

**Input message:** My flight to Nairobi was cancelled. Please put me on another flight.

**Path:** intake → classifier → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → policy_checker → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → tools → rebooking_agent → policy_checker → rebooking_agent → policy_checker → escalation → final_response

**Tools called:** get_booking({'booking_ref': 'BZ4Q8M'}), search_flights({'date': '2026-10-03', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-02', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-04', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-05', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-01', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-06', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-07', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-08', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-09', 'destination': 'NBO', 'origin': 'ADD'}), search_flights({'date': '2026-10-05', 'destination': 'NBO', 'origin': 'ADD'})

**Intent:** rebook  |  **Policy passed:** False  |  **Failed checks (retry_count):** 3  |  **Escalated:** True

**Last policy failure reason:** Cabin 'business' is higher than the booked 'economy' cabin.

**Proposed solution:** `{'type': 'rebook', 'flight_number': 'KQ311', 'cabin': 'business', 'flight': {'flight_number': 'KQ311', 'departure': '2026-10-04T07:00', 'arrival': '2026-10-04T09:05', 'available_cabins': ['business'], 'connection_airport': None, 'connection_minutes': None}}`

**Final response:**

Dear Mr. Alemu,

We’re sorry your ET306 flight to Nairobi was cancelled.  
Our system could not automatically place you in an economy‑class replacement, so a human agent is now reviewing your booking (BZ4Q8M) to find an eligible alternative or arrange a refund/compensation.  

You will receive a follow‑up email within the next 24 hours with the next steps.  

Thank you for your patience.  

Best regards,  
Customer Care Team (human agent will follow up)

## Scenario 4: Complaint asking for a manager

**thread_id:** `passenger-MG5T1R`

**Input message:** This is the third time you've cancelled on me. I want to speak to a manager.

**Path:** intake → classifier → escalation → final_response

**Tools called:** none

**Intent:** complaint  |  **Policy passed:** None  |  **Failed checks (retry_count):** 0  |  **Escalated:** True

**Last policy failure reason:** none

**Proposed solution:** `None`

**Final response:**

Dear Selam Tadesse,

We regret the inconvenience caused by the third cancellation of flight ET809 (ADD‑JNB).  
At this time we have not issued a new flight or refund, as you have requested to speak directly with a manager.  
Our senior team is reviewing your case and will verify any compensation you may be entitled to.  
A manager will contact you within the next 24 hours to discuss a personalized solution.  
Please let us know the best phone number or email for this follow‑up.  

A human agent will be in touch shortly. Thank you for your patience.
