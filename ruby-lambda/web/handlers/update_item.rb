# frozen_string_literal: true
require 'bundler/setup'
require "aws-sdk-dynamodb"

class ItemNotFoundError < StandardError; end

def lambda_handler(event:, context:)
  id = event["pathParameters"]["id"]
  item = client.get_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    key: { "id" => id }
  ).item

  raise ItemNotFoundError if item.nil?

  # body = JSON.parse(event["body"])
  item = event["body"].slice("id", "name")

  data = client.update_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    key: { "id" => id },
    update_expression: "SET #name = :name",
    expression_attribute_names: { "#name" => "name" },
    expression_attribute_values: { ":name" => item["name"] },
    return_values: "ALL_NEW"
  )

  { statusCode: 200, body: data.attributes.to_json }
rescue ItemNotFoundError
  { statusCode: 404, body: { error: "Item #{id} not found" }.to_json }
end

def client
  @client ||= Aws::DynamoDB::Client.new
end
