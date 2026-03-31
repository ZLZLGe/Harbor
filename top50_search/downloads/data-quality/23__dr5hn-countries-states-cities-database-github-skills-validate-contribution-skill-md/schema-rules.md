CSC Schema Rules Reference

Cities Table

Field
Type
Required
Constraints

name
varchar(255)
Yes
Non-empty

state_id
integer
Yes
Must exist in states table, positive

state_code
varchar(255)
Yes
Must match referenced state

country_id
integer
Yes
Must exist in countries table, positive

country_code
char(2)
Yes
Exactly 2 chars, must match referenced country ISO2

latitude
decimal(10,8)
Yes
Range: -90 to 90

longitude
decimal(11,8)
Yes
Range: -180 to 180

state_name
varchar(255)
No
Denormalised convenience field

country_name
varchar(100)
No
Denormalised convenience field

wikiDataId
varchar(255)
No
Format: Q followed by digits (e.g., Q65)

timezone
varchar(255)
No
IANA timezone string (e.g., America/New_York)

Auto-managed (must NOT be included): id, created_at, updated_at, flag

States Table

Field
Type
Required
Constraints

name
varchar(255)
Yes
Non-empty

country_id
integer
Yes
Must exist in countries table, positive

country_code
char(2)
Yes
Exactly 2 chars, must match referenced country ISO2

state_code
varchar(10)
No
Official state/province code

iso2
varchar(255)
No
ISO subdivision code

type
varchar(191)
No
Administrative division type

level
integer
No
Administrative level

parent_id
integer
No
Parent state for hierarchical divisions

native
varchar(255)
No
Native language name

fips_code
varchar(255)
No
FIPS code

latitude
decimal(10,8)
No
Range: -90 to 90

longitude
decimal(11,8)
No
Range: -180 to 180

wikiDataId
varchar(255)
No
Format: Q followed by digits

Auto-managed (must NOT be included): id, created_at, updated_at, flag

Countries Table

Field
Type
Required
Constraints

name
varchar(100)
Yes
Non-empty

iso2
char(2)
No
Exactly 2 chars

iso3
char(3)
No
Exactly 3 chars

numeric_code
char(3)
No
Exactly 3 chars

phonecode
varchar(255)
No
International dialling code

capital
varchar(255)
No
Capital city name

currency
varchar(255)
No
Currency code

currency_name
varchar(255)
No
Currency full name

currency_symbol
varchar(255)
No
Currency symbol

tld
varchar(255)
No
Top-level domain

native
varchar(255)
No
Native name

region
varchar(255)
No
World region

subregion
varchar(255)
No
World subregion

nationality
varchar(255)
No
Nationality demonym

latitude
decimal(10,8)
No
Range: -90 to 90

longitude
decimal(11,8)
No
Range: -180 to 180

emoji
varchar(191)
No
Flag emoji

emojiU
varchar(191)
No
Flag emoji unicode

wikiDataId
varchar(255)
No
Format: Q followed by digits

Auto-managed (must NOT be included): id, created_at, updated_at, flag

Foreign Key Relationships

regions -> subregions (region_id)
regions -> countries (region_id)
subregions -> countries (subregion_id)
countries -> states (country_id)
states -> cities (state_id)
countries -> cities (country_id)

Example Valid City Record

{
"name": "San Francisco",
"state_id": 1416,
"state_code": "CA",
"country_id": 233,
"country_code": "US",
"latitude": "37.77493",
"longitude": "-122.41942",
"timezone": "America/Los_Angeles"
}